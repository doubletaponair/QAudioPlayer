"""
Main window - UI, keyboard shortcuts and screen-reader behaviour.

Verbosity policy
----------------
By design the player is silent during ordinary playback. Only the following
actions speak through the screen reader:

  - Startup welcome
  - File loaded / file-not-found / unsupported-format
  - End of file
  - R (remaining time)
  - T (current and total time)
  - V (current volume and mute state)

Everything else (L, K, J, Space, arrows, number jumps, volume up/down,
mute, Home/End) only updates the visual status line without speaking.

Window sizing: audio files use the compact view (~480x150). Video files
auto-expand to ~860x560 when loaded.
"""

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFileDialog,
    QSlider,
    QFrame,
    QSizePolicy,
    QMessageBox,
    QApplication,
)

from media_engine import MediaEngine
from announcer import Announcer
from time_utils import format_time_verbal, format_time_clock
from help_dialog import HelpDialog
from updater import UpdateManager, apply_update_and_restart


# Supported formats
AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus",
    ".wma", ".aiff", ".aif", ".ape", ".mka",
}
VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".wmv",
    ".flv", ".mpg", ".mpeg", ".3gp", ".ts",
}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

# Window sizes
COMPACT_WIDTH = 480
COMPACT_HEIGHT = 150
EXPANDED_WIDTH = 860
EXPANDED_HEIGHT = 560

# Video frame height in compact mode - ONE pixel. libVLC refuses to
# decode/play a file if it cannot attach video output, so we must keep
# the frame present and native-windowed, just effectively invisible.
COMPACT_VIDEO_HEIGHT = 1
EXPANDED_VIDEO_MIN_HEIGHT = 320


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("QAudioPlayer")
        self.setAcceptDrops(True)

        # Speed tables
        self.forward_speeds = [1.0, 2.0, 3.0]
        self.reverse_speeds = [1.0, 2.0, 3.0]
        self.forward_speed_index = 0
        self.reverse_speed_index = 0

        self.is_expanded = False
        self._slider_being_dragged = False

        self.engine = MediaEngine()
        self.engine.state_changed.connect(self._on_state_changed)
        self.engine.position_changed.connect(self._on_position_changed)
        self.engine.media_ended.connect(self._on_media_ended)
        self.engine.media_loaded.connect(self._on_media_loaded)

        self.announcer = None

        self._build_ui()
        self.announcer = Announcer(self)
        self._print_diagnostics()
        self._setup_shortcuts()
        self._resize_compact()

        # Auto-update state. The check runs in the background on startup; the
        # user installs a pending update (or checks on demand) with U.
        self._pending_update = None        # (version, url) once one is found
        self._update_in_progress = False
        self._manual_check = False         # True while a user-initiated check runs
        self._update_mgr = UpdateManager(self)
        self._update_mgr.updateAvailable.connect(self._on_update_available)
        self._update_mgr.upToDate.connect(self._on_up_to_date)
        self._update_mgr.checkFailed.connect(self._on_check_failed)
        self._update_mgr.downloadProgress.connect(self._on_download_progress)
        self._update_mgr.downloadFailed.connect(self._on_download_failed)
        self._update_mgr.readyToRestart.connect(self._on_ready_to_restart)

        QTimer.singleShot(
            400,
            lambda: self._speak(
                "QAudioPlayer ready. Press O to open a file, "
                "or F1 for help."
            ),
        )

        # Let the welcome announcement finish before any update news arrives.
        QTimer.singleShot(1800, self._update_mgr.check_async)

    # ---------------- UI construction ----------------

    def _build_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.file_label = QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label)

        # Video surface. Native window is critical - VLC renders into its HWND.
        # We deliberately give it no accessible name so NVDA skips over it on
        # the initial window scan.
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.video_frame.setAttribute(
            Qt.WidgetAttribute.WA_DontCreateNativeAncestors, True
        )
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        # Trigger native window handle creation. winId() is guaranteed to
        # create one if WA_NativeWindow is set, and it exists in all PyQt6
        # builds (unlike createWinId which is missing from some wheels).
        _ = int(self.video_frame.winId())
        self.video_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.video_frame.setMinimumHeight(COMPACT_VIDEO_HEIGHT)
        self.video_frame.setMaximumHeight(COMPACT_VIDEO_HEIGHT)
        layout.addWidget(self.video_frame, stretch=1)

        # Timeline - not focusable so NVDA isn't trapped reading every tick.
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, 1000)
        self.timeline.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.timeline.sliderPressed.connect(self._on_slider_pressed)
        self.timeline.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self.timeline)

        time_row = QHBoxLayout()
        self.time_label = QLabel("0:00 / 0:00")
        time_row.addWidget(self.time_label)
        time_row.addStretch(1)
        self.state_label = QLabel("Stopped")
        time_row.addWidget(self.state_label)
        layout.addLayout(time_row)

        # Silent visual status line - does NOT speak by itself.
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

    def _print_diagnostics(self):
        """Print which announcement methods are available to the console."""
        if self.announcer is None:
            return
        methods = self.announcer.available_methods
        print("-" * 60)
        print("QAudioPlayer - startup")
        print(f"Announcement methods available: {', '.join(methods)}")
        if "NVDA Controller Client" not in methods:
            print()
            print("NOTE: For NVDA announcements (R, T, V etc.) to speak")
            print("reliably, drop nvdaControllerClient64.dll into:")
            print(f"   {os.getcwd()}")
            print("Without it, only the startup message and status text")
            print("may be picked up by NVDA.")
        print("-" * 60)

    # ---------------- Shortcut setup ----------------

    def _setup_shortcuts(self):
        bindings = [
            # QuickTime JKL
            ("L", self._on_L),
            ("K", self._on_K),
            ("J", self._on_J),

            # Transport
            ("Space", self._on_space),

            # Seeking
            ("Right", lambda: self._seek_relative(5000, "forward")),
            ("Left", lambda: self._seek_relative(-5000, "backward")),
            ("Shift+Right", lambda: self._seek_relative(30000, "forward")),
            ("Shift+Left", lambda: self._seek_relative(-30000, "backward")),
            ("Home", self._jump_to_start),
            ("End", self._jump_to_end),

            # Volume
            ("Up", lambda: self._adjust_volume(5)),
            ("Down", lambda: self._adjust_volume(-5)),
            ("M", self._toggle_mute),
            ("V", self._announce_volume),

            # Time announcements
            ("R", self._announce_remaining),
            ("T", self._announce_current_total),

            # Updates
            ("U", self._on_U),

            # File
            ("O", self._open_file_dialog),
            ("Ctrl+O", self._open_file_dialog),

            # Help dialog
            ("F1", self._show_help),
            ("Ctrl+/", self._show_help),
            ("H", self._show_help),
        ]

        for key, handler in bindings:
            sc = QShortcut(QKeySequence(key), self)
            sc.setContext(Qt.ShortcutContext.WindowShortcut)
            sc.activated.connect(handler)

        # 0-9: jump to 0%, 10% ... 90%
        for i in range(10):
            sc = QShortcut(QKeySequence(str(i)), self)
            sc.setContext(Qt.ShortcutContext.WindowShortcut)
            sc.activated.connect(lambda pct=i * 10: self._jump_percent(pct))

    # ---------------- JKL handlers ----------------

    def _on_L(self):
        if not self._require_file():
            return
        if self.engine.is_playing_forward():
            self.forward_speed_index = (
                (self.forward_speed_index + 1) % len(self.forward_speeds)
            )
        else:
            self.forward_speed_index = 0
        speed = self.forward_speeds[self.forward_speed_index]
        self.engine.play_forward(speed)
        self._status_only(f"Playing forward at {speed:g}x")

    def _on_K(self):
        if not self._require_file():
            return
        self.engine.pause()
        self._status_only("Paused")

    def _on_J(self):
        if not self._require_file():
            return
        if self.engine.is_reversing:
            self.reverse_speed_index = (
                (self.reverse_speed_index + 1) % len(self.reverse_speeds)
            )
        else:
            self.reverse_speed_index = 0
        speed = self.reverse_speeds[self.reverse_speed_index]
        self.engine.play_reverse(speed)
        self._status_only(f"Rewinding at {speed:g}x")

    def _on_space(self):
        if not self._require_file():
            return
        self.engine.toggle_play_pause()

    # ---------------- Seek / volume ----------------

    def _seek_relative(self, delta_ms, direction):
        if not self._require_file():
            return
        self.engine.seek_relative(delta_ms)
        seconds = abs(delta_ms) // 1000
        self._status_only(f"Jumped {direction} {seconds} seconds")

    def _jump_percent(self, percent):
        if not self._require_file():
            return
        self.engine.seek_percent(percent / 100.0)
        self._status_only(f"Jumped to {percent}%")

    def _jump_to_start(self):
        if not self._require_file():
            return
        self.engine.seek_percent(0.0)
        self._status_only("Start of file")

    def _jump_to_end(self):
        if not self._require_file():
            return
        self.engine.seek_percent(1.0)
        self._status_only("End of file")

    def _adjust_volume(self, delta):
        new_vol = self.engine.adjust_volume(delta)
        self._status_only(f"Volume {new_vol}%")

    def _toggle_mute(self):
        muted = self.engine.toggle_mute()
        self._status_only("Muted" if muted else "Unmuted")

    def _announce_volume(self):
        """V key - explicitly speak current volume and mute state."""
        vol = self.engine.get_volume()
        muted = self.engine.is_muted()
        if muted:
            self._speak(f"Volume {vol} percent, muted", assertive=True)
        else:
            self._speak(f"Volume {vol} percent", assertive=True)

    # ---------------- Time announcements ----------------

    def _announce_remaining(self):
        if not self._require_file():
            return
        ms = self.engine.get_remaining_ms()
        self._speak(f"{format_time_verbal(ms)} remaining", assertive=True)

    def _announce_current_total(self):
        if not self._require_file():
            return
        cur = format_time_verbal(self.engine.get_position_ms())
        tot = format_time_verbal(self.engine.get_duration_ms())
        self._speak(f"{cur} of {tot}", assertive=True)

    # ---------------- Help ----------------

    def _show_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    # ---------------- File open ----------------

    def _open_file_dialog(self):
        audio = " ".join(f"*{ext}" for ext in sorted(AUDIO_EXTENSIONS))
        video = " ".join(f"*{ext}" for ext in sorted(VIDEO_EXTENSIONS))
        filters = (
            f"Media files ({audio} {video});;"
            f"Audio files ({audio});;"
            f"Video files ({video});;"
            f"All files (*.*)"
        )
        path, _ = QFileDialog.getOpenFileName(self, "Open media file", "", filters)
        if path:
            self.open_file(path)

    def open_file(self, path):
        if not os.path.isfile(path):
            self._speak(f"File not found: {path}")
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            self._speak(f"Unsupported file type: {ext}")
            return

        # Attach the native video surface BEFORE loading. Calling winId()
        # during construction already forced the HWND to exist, so it's
        # always valid regardless of whether the frame is 1 px or 320 px tall.
        self.engine.set_video_widget(self.video_frame)
        self.engine.load(path)

        name = os.path.basename(path)
        self.file_label.setText(name)
        self.setWindowTitle(f"{name} - QAudioPlayer")

        # Auto-resize based on file type: video files get the expanded view
        # so there's something to see; audio files stay compact.
        if ext in VIDEO_EXTENSIONS:
            self._resize_expanded()
        else:
            self._resize_compact()

        self._speak(f"Loaded {name}. Press L to play.")

    # ---------------- Window size ----------------

    def _resize_compact(self):
        self.is_expanded = False
        self.video_frame.setMinimumHeight(COMPACT_VIDEO_HEIGHT)
        self.video_frame.setMaximumHeight(COMPACT_VIDEO_HEIGHT)
        self.resize(COMPACT_WIDTH, COMPACT_HEIGHT)

    def _resize_expanded(self):
        self.is_expanded = True
        self.video_frame.setMinimumHeight(EXPANDED_VIDEO_MIN_HEIGHT)
        self.video_frame.setMaximumHeight(16777215)
        self.resize(EXPANDED_WIDTH, EXPANDED_HEIGHT)

    # ---------------- Engine signal handlers ----------------

    def _on_state_changed(self, state):
        labels = {
            "playing": "Playing",
            "paused": "Paused",
            "stopped": "Stopped",
            "reversing": "Rewinding",
        }
        self.state_label.setText(labels.get(state, state.capitalize()))

    def _on_position_changed(self, position_ms, duration_ms):
        if self._slider_being_dragged:
            return
        if duration_ms > 0:
            self.timeline.blockSignals(True)
            self.timeline.setValue(int(1000 * position_ms / duration_ms))
            self.timeline.blockSignals(False)
        self.time_label.setText(
            f"{format_time_clock(position_ms)} / {format_time_clock(duration_ms)}"
        )

    def _on_media_ended(self):
        self._speak("End of file", assertive=True)

    def _on_media_loaded(self, filepath):
        QTimer.singleShot(600, self.engine._emit_position)

    def _on_slider_pressed(self):
        self._slider_being_dragged = True

    def _on_slider_released(self):
        self._slider_being_dragged = False
        value = self.timeline.value()
        self.engine.seek_percent(value / 1000.0)

    # ---------------- Drag and drop ----------------

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.open_file(path)

    # ---------------- Helpers ----------------

    def _require_file(self):
        if not self.engine.current_file:
            self._speak("No file loaded. Press O to open a file.")
            return False
        return True

    def _speak(self, message, assertive=False):
        """Speak through the screen reader AND update the status label."""
        if self.announcer:
            self.announcer.announce(message, assertive=assertive)
        self.status_label.setText(message)

    def _status_only(self, message):
        """Update the visible status line but do NOT speak."""
        self.status_label.setText(message)

    # ---------------- Updates ----------------

    def _on_U(self):
        """U - install a pending update, or check for one if none is known."""
        if self._update_in_progress:
            self._speak("An update is already downloading.", assertive=True)
            return
        if self._pending_update:
            version, url = self._pending_update
            answer = QMessageBox.question(
                self,
                "Install update",
                f"QAudioPlayer {version} is available.\n\n"
                f"Install it now? The app will close and reopen automatically.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._update_in_progress = True
                self._speak(f"Downloading update version {version}.", assertive=True)
                self._update_mgr.download_and_apply_async(url)
        else:
            self._manual_check = True
            self._speak("Checking for updates.", assertive=True)
            self._update_mgr.check_async()

    def _on_update_available(self, version, url):
        self._pending_update = (version, url)
        self._manual_check = False
        self._speak(
            f"QAudioPlayer update available, version {version}. Press U to install.",
            assertive=True,
        )

    def _on_up_to_date(self, version):
        # Routine startup checks stay silent; only report when the user asked.
        if self._manual_check:
            self._manual_check = False
            self._speak(
                f"You are running the latest version, {version}.", assertive=True
            )

    def _on_check_failed(self, message):
        # Don't nag on a routine startup check (e.g. offline). Report only when
        # the user explicitly asked.
        if self._manual_check:
            self._manual_check = False
            self._speak(
                "Could not check for updates. Check your internet connection.",
                assertive=True,
            )

    def _on_download_progress(self, done, total):
        if total:
            self._status_only(f"Downloading update: {int(done * 100 / total)}%")

    def _on_download_failed(self, message):
        self._update_in_progress = False
        self._speak("Update download failed. Please try again later.", assertive=True)

    def _on_ready_to_restart(self, new_exe_path):
        self._speak("Update downloaded. Restarting QAudioPlayer.", assertive=True)
        try:
            apply_update_and_restart(new_exe_path)
        except Exception:
            self._update_in_progress = False
            self._speak("Could not apply the update.", assertive=True)
            return
        # Give NVDA a moment to speak, then quit so the swap can complete.
        QTimer.singleShot(1200, QApplication.instance().quit)

    # ---------------- Clean shutdown ----------------

    def closeEvent(self, event):
        try:
            self.engine.stop()
        except Exception:
            pass
        event.accept()
