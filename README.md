# QAudioPlayer

A keyboard-first, screen-reader-friendly audio and video player for Windows.
Inspired by QuickTime Audio on the Mac, with its JKL transport controls and
pitch-preserved speed changes, but available on the PC and built from the
ground up to work with NVDA and JAWS.

---

## Features

- **QuickTime-style JKL controls** - L plays forward, K pauses, J rewinds.
  Repeated presses cycle through 1x, 2x and 3x.
- **Pitch-preserved speed** - 2x and 3x sound natural, not chipmunked,
  thanks to libVLC's scaletempo audio filter.
- **Reverse playback** - silent timer-based rewind that works consistently
  across every supported format.
- **Remaining-time shortcut** - press R to hear how much time is left.
  Press T to hear elapsed and total time. Press V to hear current volume.
- **Auto-sizing window** - audio files use a compact ~480 x 150 window
  (QuickTime Audio size). Video files automatically expand to ~860 x 560.
- **Every file format you need** - MP3, WAV, M4A, AAC, FLAC, OGG, Opus, WMA,
  MP4, MOV, M4V, AVI, MKV, WebM, WMV and more (whatever libVLC supports).
- **Drag and drop** - drop a file onto the window to load it.
- **Full keyboard control** - no mouse required. Every action has a shortcut.
- **Silent by default** - the app only speaks when you explicitly ask for
  information (R, T, V) or when something significant happens (file loaded,
  end of file). Playback controls update the visual status line but do
  not speak.

---

## Keyboard shortcuts

### Transport (QuickTime-style)

| Key   | Action                                                  |
|-------|---------------------------------------------------------|
| L     | Play forward. Press again to cycle 1x / 2x / 3x.        |
| K     | Pause (keeps position).                                 |
| J     | Rewind. Press again to cycle 1x / 2x / 3x.              |
| Space | Toggle play / pause (always resumes forward at 1x).     |

### Seeking

| Key                 | Action                                    |
|---------------------|-------------------------------------------|
| Right / Left arrow  | Jump forward / backward 5 seconds.        |
| Shift + arrow       | Jump forward / backward 30 seconds.       |
| Home                | Jump to start of file.                    |
| End                 | Jump to end of file.                      |
| 0 - 9               | Jump to 0%, 10%, 20% ... 90% of the file. |

### Volume

| Key              | Action                                          |
|------------------|-------------------------------------------------|
| Up / Down arrow  | Volume up / down by 5.                          |
| M                | Toggle mute.                                    |
| V                | Speak current volume and mute state.            |

### Time announcements

| Key | Action                                                       |
|-----|--------------------------------------------------------------|
| R   | Speak remaining time (e.g. "3 minutes 42 seconds remaining").|
| T   | Speak current and total time.                                |

### File and help

| Key                  | Action                                                 |
|----------------------|--------------------------------------------------------|
| O or Ctrl + O        | Open a file.                                           |
| F1, H, or Ctrl + /   | Show keyboard shortcuts dialog.                        |
| Escape (in dialog)   | Close the help dialog.                                 |

---

## Installation

### Path 1 - Install the .exe (recommended)

1. Install VLC media player (64-bit) from https://www.videolan.org/vlc/
   The app uses libVLC at runtime, so VLC must be present on your PC.
2. Run `QAudioPlayerSetup.exe`.
3. When the installer finishes it will offer to open Windows
   Settings > Apps > Default apps. To make this app your default for media
   files, scroll in that settings page and set QAudioPlayer as the
   handler for each file type you want.

### Path 2 - Run from source

1. Install Python 3.10 or later (64-bit) from https://www.python.org/
   Tick "Add python.exe to PATH" during installation.
2. Install VLC (64-bit) as in Path 1.
3. Open a Command Prompt in the folder containing this README and run:

   ```
   pip install -r requirements.txt
   python main.py
   ```

To build your own `QAudioPlayer.exe`:

```
pip install pyinstaller
build.bat
```

The .exe will appear in the `dist` folder. You can then build the full
installer by compiling `installer.iss` with Inno Setup 6.3 or later.

---

## System requirements

- Windows 10 1809 or later, OR Windows 11 (any build)
- 64-bit (x64) or ARM64 (runs via x64 emulation on ARM64 PCs)
- VLC media player 64-bit installed

---

## Notes on accessibility

The player is built around NVDA on Windows but works with JAWS and Narrator too.

- **Global shortcuts** - every action is a keystroke. The timeline slider
  is deliberately not focusable so that NVDA won't be pulled into reading
  every small position change.
- **Silent by default** - playback controls don't speak; you query
  information explicitly with R, T or V when you want it.
- **NVDA Controller Client** - the app talks directly to NVDA via the
  Controller Client DLL for reliable speech that doesn't depend on UIA
  events. The DLL is bundled inside the .exe.
- **Help dialog** - the keyboard shortcuts window uses a list widget with
  one item per line, so arrowing up and down reads each key and action
  cleanly without table verbosity.

---

## Troubleshooting

**"Failed to start the media engine"**
VLC is not installed, or only the 32-bit version is installed while Python
is 64-bit. Install the 64-bit VLC from https://www.videolan.org/vlc/

**No sound at 2x / 3x**
Make sure the scaletempo filter is available. It ships with standard VLC -
if you use a minimal VLC build you may need to re-enable it.

**R doesn't speak**
The NVDA Controller Client DLL didn't load. If running from source, drop
`nvdaControllerClient64.dll` into the project folder. If running the .exe,
this shouldn't happen - the DLL is bundled inside.

---

## Licence

Your project - licence it however suits you. The dependencies have their
own licences:
- PyQt6 is GPL v3 or commercial.
- python-vlc is LGPL v2.1+.
- libVLC (installed separately by the user) is LGPL v2.1+.
- NVDA Controller Client is part of NVDA, licensed under GPL v2+.
