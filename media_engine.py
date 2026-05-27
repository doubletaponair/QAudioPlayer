"""
Media engine - wraps python-vlc with pitch-preserved speed control and
reliable timer-based reverse playback.

Notes on libVLC quirks fixed here:

1. media_player.pause() is a TOGGLE in libVLC - calling it when paused
   resumes playback. This caused "intermittent forward playback" when
   pressing J after L. We now use set_pause(1) / set_pause(0) which are
   explicit set-states.

2. set_rate(-1.0) returns 0 ("success") even when the backend cannot do
   reverse playback - it just silently fails. Rather than detect this
   unreliably we always use timer-based backward scrubbing for reverse.
   Result: reverse is silent but it actually works, on every format.
"""

import sys

import vlc
from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class MediaEngine(QObject):
    state_changed = pyqtSignal(str)         # playing / paused / stopped / reversing
    position_changed = pyqtSignal(int, int) # position_ms, duration_ms
    media_ended = pyqtSignal()
    media_loaded = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        vlc_args = [
            "--audio-filter=scaletempo",  # pitch preservation at 2x / 3x
            "--no-video-title-show",
            "--quiet",
        ]
        self.vlc_instance = vlc.Instance(vlc_args)
        if self.vlc_instance is None:
            raise RuntimeError(
                "Could not initialise libVLC. Please install VLC 64-bit from "
                "https://www.videolan.org/vlc/"
            )
        self.media_player = self.vlc_instance.media_player_new()

        self.current_file = None
        self._cached_duration_ms = 0

        # Reverse (backward scrub) state
        self.is_reversing = False
        self.reverse_speed = 1.0
        self.reverse_timer = QTimer(self)
        self.reverse_timer.setInterval(40)  # 25 Hz
        self.reverse_timer.timeout.connect(self._reverse_tick)

        # Position update timer for the UI
        self.position_timer = QTimer(self)
        self.position_timer.setInterval(200)
        self.position_timer.timeout.connect(self._emit_position)
        self.position_timer.start()

        ev = self.media_player.event_manager()
        ev.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

    # ---------------- Loading ----------------

    def load(self, filepath):
        self.stop()
        media = self.vlc_instance.media_new(filepath)
        self.media_player.set_media(media)
        self.current_file = filepath
        self._cached_duration_ms = 0
        try:
            media.parse_with_options(vlc.MediaParseFlag.local, 3000)
        except AttributeError:
            try:
                media.parse()
            except Exception:
                pass
        self.media_loaded.emit(filepath)

    # ---------------- Transport ----------------

    def play_forward(self, speed=1.0):
        """Play forward at given speed. Pitch preserved by scaletempo."""
        self._stop_reverse()
        if self._player_has_ended():
            # End of file is terminal in libVLC: play() is ignored until the
            # media is re-set. Reload so playback restarts from the beginning.
            self._reload_media()
        try:
            if not self.media_player.is_playing():
                self.media_player.play()
        except Exception:
            self.media_player.play()
        self.media_player.set_rate(float(speed))
        self.state_changed.emit("playing")

    def play_reverse(self, speed=1.0):
        """Rewind backward at given speed via timer-based scrubbing (silent)."""
        if self._player_has_ended():
            # Revive a player that hit end-of-file so it isn't frozen.
            self._reload_media()
        self.reverse_speed = float(speed)
        # Explicit pause so audio stops. pause() is a TOGGLE in libVLC,
        # so we use set_pause(1) which is a set-state.
        try:
            self.media_player.set_pause(1)
        except Exception:
            pass
        try:
            self.media_player.set_rate(1.0)
        except Exception:
            pass
        self.is_reversing = True
        if not self.reverse_timer.isActive():
            self.reverse_timer.start()
        self.state_changed.emit("reversing")

    def _reverse_tick(self):
        if not self.is_reversing:
            return
        current = self.media_player.get_time()
        if current is None or current <= 0:
            self._stop_reverse()
            self.state_changed.emit("paused")
            return
        step_ms = int(40 * self.reverse_speed)
        new_time = max(0, current - step_ms)
        self.media_player.set_time(new_time)

    def _stop_reverse(self):
        if self.is_reversing:
            self.is_reversing = False
            self.reverse_timer.stop()

    def pause(self):
        """Pause - keeps position."""
        self._stop_reverse()
        try:
            self.media_player.set_pause(1)  # explicit pause (not toggle)
        except Exception:
            if self.media_player.is_playing():
                self.media_player.pause()
        self.state_changed.emit("paused")

    def stop(self):
        self._stop_reverse()
        self.media_player.stop()
        self.state_changed.emit("stopped")

    def toggle_play_pause(self):
        """Space-style toggle. Always resumes forward at 1x if starting."""
        if self.is_reversing:
            self.pause()
            return
        if self.media_player.is_playing():
            try:
                self.media_player.set_pause(1)
            except Exception:
                self.media_player.pause()
            self.state_changed.emit("paused")
        else:
            if self._player_has_ended():
                self._reload_media()
            self.media_player.set_rate(1.0)
            self.media_player.play()
            self.state_changed.emit("playing")

    def is_playing_forward(self):
        return self.media_player.is_playing() and not self.is_reversing

    # ---------------- Seeking ----------------

    def seek_relative(self, delta_ms):
        if self._player_has_ended():
            # Reading/seeking is ignored on an ended player - revive it first.
            self._reload_media()
            self.media_player.play()
            self.state_changed.emit("playing")
        current = self.media_player.get_time() or 0
        duration = self.get_duration_ms()
        if duration <= 0:
            duration = max(current + abs(delta_ms), 0)
        new_time = max(0, min(duration, current + delta_ms))
        self.media_player.set_time(new_time)

    def seek_percent(self, fraction):
        fraction = max(0.0, min(1.0, fraction))
        if self._player_has_ended():
            # Revive an ended player, then seek to the requested point.
            self._reload_media()
            self.media_player.play()
            self.state_changed.emit("playing")
        self.media_player.set_position(fraction)

    def seek_to_end(self):
        """Jump to just before the end and park there, paused.

        We deliberately stop ~half a second short of the absolute end. Seeking
        to the very end drives libVLC into its terminal 'Ended' state, after
        which it ignores play/seek until the media is reloaded (this was the
        'nothing plays after pressing End' bug). Parking just before the end,
        paused, keeps the player alive and fully controllable.
        """
        self._stop_reverse()
        if self._player_has_ended():
            self._reload_media()
        # set_time / set_position only take effect on a live (playing or
        # paused) player, so make sure it has started first.
        try:
            state = self.media_player.get_state()
        except Exception:
            state = None
        if state not in (vlc.State.Playing, vlc.State.Paused):
            self.media_player.play()
        duration = self.get_duration_ms()
        if duration > 0:
            self.media_player.set_time(max(0, duration - 500))
        else:
            self.media_player.set_position(0.999)
        try:
            self.media_player.set_pause(1)
        except Exception:
            pass
        self.state_changed.emit("paused")

    # ---------------- Volume ----------------

    def set_volume(self, volume):
        volume = max(0, min(100, int(volume)))
        self.media_player.audio_set_volume(volume)
        return volume

    def get_volume(self):
        v = self.media_player.audio_get_volume()
        return max(0, v if v is not None else 0)

    def adjust_volume(self, delta):
        return self.set_volume(self.get_volume() + delta)

    def toggle_mute(self):
        self.media_player.audio_toggle_mute()
        return bool(self.media_player.audio_get_mute())

    def is_muted(self):
        return bool(self.media_player.audio_get_mute())

    # ---------------- Position / duration ----------------

    def get_position_ms(self):
        v = self.media_player.get_time()
        return max(0, v if v is not None else 0)

    def get_duration_ms(self):
        v = self.media_player.get_length()
        if v is not None and v > 0:
            self._cached_duration_ms = v
        return self._cached_duration_ms

    def get_remaining_ms(self):
        pos = self.get_position_ms()
        dur = self.get_duration_ms()
        return max(0, dur - pos)

    # ---------------- Video ----------------

    def set_video_widget(self, widget):
        """Attach VLC's video output to a native widget."""
        try:
            wid = int(widget.winId())
        except Exception:
            return
        if sys.platform.startswith("win"):
            self.media_player.set_hwnd(wid)
        elif sys.platform == "darwin":
            self.media_player.set_nsobject(wid)
        else:
            self.media_player.set_xwindow(wid)

    def has_video(self):
        try:
            return (self.media_player.video_get_track_count() or 0) > 0
        except Exception:
            return False

    # ---------------- Internals ----------------

    def _emit_position(self):
        if self.current_file:
            self.position_changed.emit(
                self.get_position_ms(),
                self.get_duration_ms(),
            )

    def _player_has_ended(self):
        """True if libVLC is in a terminal state (Ended/Error) where play(),
        set_time() and set_position() are silently ignored until the media is
        re-set. See _reload_media()."""
        try:
            return self.media_player.get_state() in (
                vlc.State.Ended, vlc.State.Error
            )
        except Exception:
            return False

    def _reload_media(self):
        """Re-set the current file so the player leaves the terminal Ended
        state and becomes controllable again. Leaves it stopped at position 0;
        the caller restarts playback as needed. The video output (HWND) lives
        on the player, not the media, so it survives this."""
        if not self.current_file:
            return
        try:
            media = self.vlc_instance.media_new(self.current_file)
            self.media_player.set_media(media)
        except Exception:
            pass

    def _on_end_reached(self, event):
        self.media_ended.emit()
