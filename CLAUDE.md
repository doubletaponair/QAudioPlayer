# CLAUDE.md — QAudioPlayer

This document briefs Claude Code on the QAudioPlayer project so
iteration can continue locally on the user's PC. Read it fully before
making changes.

---

## Who you're working with

**Steven Scott** — blind co-host and producer of the Double Tap podcast
(AMI / accessibility tech focus). He drives Windows with NVDA, is a
keyboard-first user, and has strong opinions about accessible UI. He uses
VoiceOver on Mac. His standard episode length is 56 minutes — many of the
audio files he opens will be in that range.

Treat him as a sophisticated end-user *and* a domain expert on
accessibility. He will spot verbosity, redundant announcements, and
focus-trapping behaviour faster than you will.

---

## Project overview

A keyboard-first, NVDA-friendly media player for Windows, inspired by
QuickTime Audio on macOS. Built because no Windows equivalent existed
with proper JKL transport, pitch-preserved speed control, and tight
keyboard focus that doesn't trap a screen reader.

The user-facing brief:

- L plays forward at 1x; press again to cycle 1x → 2x → 3x
- K pauses (keeps position)
- J rewinds; press again to cycle 1x → 2x → 3x
- Pitch is preserved at all speeds (no chipmunk effect)
- R speaks remaining time; T speaks elapsed/total; V speaks volume state
- Compact ~480×150 window for audio; auto-expands to ~860×560 for video
- Plays MP3, WAV, M4A, AAC, FLAC, OGG, OPUS, WMA, MP4, MOV, M4V, AVI,
  MKV, WebM, WMV and more (whatever libVLC supports)
- Goal: be the user's default media player on Windows

---

## Tech stack

- **Python 3.14** (the user has this installed; see "Known Python 3.14
  quirks" below). Python 3.13 is a fine fallback if 3.14 wheels keep
  causing problems.
- **PyQt6** for UI (`pip install PyQt6`)
- **python-vlc** as the media engine (`pip install python-vlc`)
- **VLC 64-bit** must be installed system-wide — used at runtime via
  libVLC, not bundled. Available from https://www.videolan.org/vlc/
- **nvdaControllerClient64.dll** sits in the project root and is bundled
  into the .exe at build time. This is how the app speaks through NVDA.
- **PyInstaller** for building `QAudioPlayer.exe` (`pip install pyinstaller`)
- **Inno Setup 6.3+** (6.7.3 installed per-user at `%LOCALAPPDATA%\Programs\Inno Setup 6`) for the installer

---

## File map

Working directory on Steven's PC: `C:\QPlayerBuild\`

| File | Role |
|------|------|
| `main.py` | Entry point. Creates QApplication, surfaces startup errors in a dialog, handles command-line file arguments (for file associations). |
| `main_window.py` | UI layout, keyboard shortcuts, screen-reader behaviour. The biggest file. |
| `media_engine.py` | Wraps python-vlc. Pitch preservation, timer-based reverse playback, volume, seeking. |
| `announcer.py` | Sends text to NVDA via the Controller Client DLL. Falls back to Qt's `QAccessibleAnnouncementEvent` (if available) and silent visual status as a last resort. |
| `help_dialog.py` | Modal dialog with the keyboard shortcut list. Uses `QListWidget` with one item per line (key, then action). |
| `time_utils.py` | Time formatting — `format_time_clock` (display) and `format_time_verbal` (spoken). |
| `requirements.txt` | Python deps. |
| `build.bat` | PyInstaller build. Bundles `nvdaControllerClient64.dll` via `--add-binary` when present. |
| `installer.iss` | Inno Setup script. x64compatible (covers x64 and ARM64-via-emulation), MinVersion 10.0.17763, includes VLC presence check. |
| `nvdaControllerClient64.dll` | NVDA Controller Client (renamed from `nvdaControllerClient.dll` x64 build, downloaded from NVDA's GitHub releases controllerClient package). |
| `README.md` | End-user docs. |

Build artefacts (gitignore these if you add git later):
- `build/` and `dist/` from PyInstaller
- `QAudioPlayer.spec` from PyInstaller
- `Output/` from Inno Setup (contains the final `QAudioPlayerSetup.exe`)
- `__pycache__/`

---

## How everything fits together

```
User keypress
    ↓
QShortcut in main_window.py
    ↓
Handler method on MainWindow (e.g. _on_L)
    ↓
MediaEngine method (e.g. play_forward(speed))
    ↓
python-vlc → libvlc.dll → audio/video output

Status updates flow back:
MediaEngine emits signal (state_changed, position_changed, media_ended)
    ↓
MainWindow signal handler updates UI labels
    ↓
For "speak" actions (R/T/V/file-loaded/end-of-file):
    Announcer.announce()
    ↓
    NVDA Controller Client DLL → NVDA process → speech
```

---

## Verbosity policy (important — don't break this)

The app is **silent during ordinary playback**. Steven explicitly asked
for this and pushed back when it was too chatty. The only things that
speak through NVDA are:

| Trigger | What's spoken |
|---|---|
| App startup | "QAudioPlayer ready. Press O to open a file, or F1 for help." |
| File loaded | "Loaded {filename}. Press L to play." |
| File not found / unsupported format | Error message |
| End of file reached | "End of file" |
| R | Remaining time as words |
| T | Current and total time as words |
| V | Volume and mute state |
| Update found (startup or U) | "QAudioPlayer update available, version X. Press U to install." |
| U (no update / manual check) | "You are running the latest version" (only when the user pressed U) |
| Update download + apply | "Downloading update…" then "Update downloaded. Restarting QAudioPlayer." |

L, K, J, Space, arrow seeking, number jumps, volume up/down, mute, drag-and-drop
file load all update the visible status line but **do not speak**.
`_status_only()` updates the visible label; `_speak()` updates *and* speaks.

When adding new features, default to silent unless there's a clear reason
the user needs to be told something they can't query.

---

## Accessibility approach

**Announcement channel.** The Announcer tries paths in this order:

1. NVDA Controller Client DLL — most reliable for NVDA users
2. `QAccessibleAnnouncementEvent` (Qt 6.8+) — works for JAWS/Narrator/NVDA
   when the Python build exposes `QAccessible`
3. Silent fallback — status label updates but doesn't speak

When the app starts, `_print_diagnostics()` prints which methods are
active to stdout. Useful for debugging.

**Accessible names.** Deliberately minimal. Steven complained about NVDA
reading "QAudioPlayer grouping, Video display area button..."
on launch. Solution: removed `setAccessibleName` from widgets that don't
need it. NVDA reads QLabel text natively; adding a name on top duplicates.

**Focus model.** The timeline slider has `FocusPolicy.NoFocus` —
otherwise NVDA gets trapped reading every position change. All seeking is
keyboard-driven via shortcuts, not via the slider.

**Help dialog.** Uses `QListWidget` with two items per shortcut (key, then
action). `QTableWidget` was tried first and was rejected because NVDA
announced "data item, selected, row 1, column 1" on every cell.
`QPlainTextEdit` was tried second and was rejected because NVDA's caret
tracking didn't follow the cursor between lines reliably. The list widget
gives a clean "L" / "Play forward..." reading pattern.

---

## Known Python 3.14 quirks

The Python 3.14 PyQt6 wheels (as of writing) are missing some classes
and methods that mature builds expose. Hit so far:

- `QAccessible` not exposed → announcer falls back gracefully
- `QFrame.createWinId()` not exposed → use `int(widget.winId())` instead
  (already done)

**If you hit "cannot import name X" or "Y object has no attribute Z"
errors during iteration**, the answer is almost always one of:

1. Find an alternative API that's available in the slim wheel
2. Code defensively with try/except around the missing thing
3. Tell Steven to install Python 3.13 alongside and use `py -3.13 main.py`

Don't waste time fighting the wheel — work around it.

---

## libVLC gotchas already solved (don't reintroduce these bugs)

1. **`media_player.pause()` is a toggle**, not "pause". Calling it when
   already paused resumes playback. Always use `media_player.set_pause(1)`
   for explicit pause and `set_pause(0)` for explicit resume. This caused
   an "intermittent forward playback after pressing J" bug early on.

2. **`set_rate(-n)` returns success even when reverse is unsupported.**
   You cannot trust it. We don't use native reverse at all. Reverse is
   implemented by pausing and using a 25 Hz QTimer to step the playback
   position backwards. Result: rewind is always silent (intentionally —
   Steven prefers consistent behaviour over format-dependent audio).

3. **Video output requires a valid native HWND at all times.** If you
   set the video frame's `maximumHeight=0`, libVLC silently refuses to
   play the file *including audio*. The current code keeps the frame at
   1 px in compact mode and calls `int(self.video_frame.winId())` during
   construction to force the HWND to exist before any media loads.

4. **Window auto-resizes by file type.** Audio extension → compact view.
   Video extension → expanded view. No F-key toggle; that was tried and
   removed because Steven doesn't need to see video in compact mode
   anyway.

---

## Auto-update (GitHub Releases)

The app updates itself from this repo's **GitHub Releases**. Files:

- `version.py` — `__version__`, the single source of truth. Bump it per release.
- `updater.py` — pure helpers (`check_for_update`, `download_update`,
  `apply_update_and_restart`) plus a Qt `UpdateManager` that runs the network
  work on a background thread and reports back via signals. Stdlib only
  (`urllib`/`ssl`/`json`) — no new bundle deps.

Flow: on startup `main_window` calls `UpdateManager.check_async()` (delayed
1.8 s so the welcome speaks first). It GETs the repo's `releases/latest`,
compares the tag (e.g. `v1.0.1`) to `__version__`, and if newer **and** the
release has a `QAudioPlayer.exe` asset, announces it. **U** confirms via a
dialog, downloads the new exe next to the running one, then a detached
`.bat` waits for the process to exit, swaps the exe, and relaunches.

Because the app is installed **per-user** in `%LOCALAPPDATA%\QAudioPlayer`,
the self-replace needs **no admin/UAC**. (This is why we moved off the
Program Files install.) Running from source can check but can't self-apply
(`sys.frozen` guard) — it announces that gracefully.

**To ship an update:** bump `version.py`, commit/push, rebuild the exe, and
`gh release create vX.Y.Z dist\QAudioPlayer.exe`. The asset MUST be named
`QAudioPlayer.exe` (matches `updater.ASSET_NAME` and `build.bat --name`).
Startup checks are silent when current and fail silently when offline.

---

## Keyboard map (current truth)

```
L                       Play forward, cycles 1x/2x/3x on repeat
K                       Pause
J                       Rewind, cycles 1x/2x/3x on repeat
Spacebar                Toggle play/pause (resumes at 1x forward)

Left / Right            Seek -5s / +5s (silent)
Shift+Left / Shift+Right  Seek -30s / +30s (silent)
Home / End              Jump to start / end of file (silent)
0-9                     Jump to 0/10/20...90% of file (silent)

Up / Down               Volume +5 / -5 (silent — query with V)
M                       Toggle mute (silent — query with V)
V                       Speak current volume and mute state

R                       Speak remaining time
T                       Speak elapsed of total time

U                       Check for / install app updates (see Auto-update below)

O / Ctrl+O              Open file dialog
F1 / H / Ctrl+/         Show keyboard shortcuts dialog
Escape (in dialog)      Close dialog
```

If you add a new shortcut, update `main_window.py`'s bindings list AND
`help_dialog.py`'s `SHORTCUTS` list — they're not auto-synced. Also
update this document.

---

## Running, building, distributing

**Run from source (Steven's day-to-day for testing):**
```
cd /d C:\QPlayerBuild
python main.py
```

**Build standalone .exe:**
```
pip install pyinstaller    # one-off
build.bat
```
Output: `dist\QAudioPlayer.exe`. The DLL is bundled inside.

**Build installer:**
Inno Setup 6.7.3 is installed **per-user** on the PC at
`%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe` (via winget,
`JRSoftware.InnoSetup`). Compile from the project dir:
```
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer.iss
```
Output: `Output\QAudioPlayerSetup.exe`. `installer.iss` is a **per-user**
install (`PrivilegesRequired=lowest`, `DefaultDirName={localappdata}\QAudioPlayer`,
all registry via `HKA`→HKCU) — this is deliberate so the auto-updater can
self-replace without UAC. Don't revert it to a Program Files / HKLM install.

**Distribution target arches:**
- Windows 10 x64 (1809+) — native
- Windows 11 x64 — native
- Windows 11 ARM64 — via Prism x64 emulation (transparent to user)
- Windows 10 ARM64 — via older x64 emulation (works, slower)

Older Windows is rejected with a friendly message via the
`MinVersion=10.0.17763` directive.

If true ARM64 native is ever wanted, that requires a separate build on
ARM64 hardware/VM with ARM64 Python+PyQt6+VLC, then a multi-binary
installer that picks the right .exe by arch.

---

## Iteration etiquette

Things Steven has been clear about that you should preserve:

- **Silent playback by default.** Don't add speech to L/K/J/Space/arrows/
  numbers/volume/mute. Only the actions in the verbosity table above
  should speak.
- **Compact window stays compact for audio.** Don't auto-grow it.
- **Help dialog uses a list widget, not a table.** NVDA verbosity test:
  arrowing through items should yield clean "L" → "Play forward..."
  reads with no row/column/data-item decoration. If you change the widget
  type, test with NVDA before declaring it done.
- **Time announcements use word form** ("3 minutes 42 seconds"), not
  clock form ("3:42"). NVDA reads ":" as "colon" which is awful.
- **Always update the on-screen status label even for silent actions.**
  Sighted users (or NVDA users using object navigation) can still read
  what just happened.

Things to ask Steven about before changing:

- Window sizes (he settled on 480x150 and 860x560 by feel; ask before
  altering)
- Any change to L/K/J behaviour (this is the core of the QuickTime parity)
- Removing or rebinding shortcuts he uses (R, T, V especially)

Things you can change freely:

- Internal code structure, refactoring, comments
- New optional features (bonus shortcuts, new dialogs) **as long as
  defaults stay silent and existing shortcuts keep working**
- Anything cosmetic on the visible UI (he can't see it)

---

## How to test changes locally

After editing files in `C:\QPlayerBuild`:

```
cd /d C:\QPlayerBuild
python main.py
```

There's no test suite (yet). Manual test checklist for any change
affecting playback or shortcuts:

1. Diagnostic print shows "NVDA Controller Client" in available methods
2. Welcome announcement speaks on launch
3. Open an MP3 → loaded message speaks; window stays compact
4. L plays at 1x → press L → 2x → press L → 3x → press L → 1x (silent throughout)
5. K pauses (silent)
6. J rewinds (status label changes, position moves backward, silent)
7. R speaks remaining time as words
8. T speaks elapsed of total
9. V speaks volume; Up arrow then V should report 5 higher
10. M mutes; V should now say "muted"; M again unmutes
11. Open an MP4 → window auto-expands; video visible; audio plays
12. Open an MP3 again → window auto-shrinks
13. F1 opens help dialog; arrowing reads "L" then "Play forward..." cleanly

If anything in that list regresses, you broke something.

---

## Things on the wishlist (not built yet)

These came up in conversation but aren't implemented. Don't assume; ask
Steven before starting any of them:

- Playlist / queue support
- Bookmarks within a file (e.g. press B to mark current position)
- Automatic resume from last position when reopening a file
- Loop / A-B repeat
- Per-file speed memory (so a podcast reopens at the speed you last used)
- Equaliser / audio boost
- Subtitle support for video
- More granular speed steps (1.25, 1.5, 1.75)

---

## Git status

There's no git repo on disk as of this handoff. If you set one up,
`.gitignore` should include:

```
build/
dist/
Output/
__pycache__/
*.pyc
*.spec
nvdaControllerClient64.dll
```

The DLL is excluded because it's redistributed under NVDA's licence and
should be fetched fresh from the NVDA releases page rather than vendored
into the repo. The build process handles it being absent gracefully (it
just warns and produces an exe with no NVDA support).

---

## Contact

When in doubt, ask Steven directly. He's responsive and prefers a quick
clarifying question to a wrong implementation he then has to undo.
