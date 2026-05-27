"""
Auto-update support backed by GitHub Releases.

Flow
----
On startup the app runs `UpdateManager.check_async()` on a background thread.
It asks the GitHub API for the repo's *latest* release, compares the release
tag (e.g. "v1.0.1") against the bundled `__version__`, and if the release is
newer and ships a `QAudioPlayer.exe` asset, emits `updateAvailable`.

When the user presses U and confirms, `download_and_apply_async()` downloads
the new exe next to the running one, then a small detached batch file waits
for this process to exit, swaps the exe, and relaunches it. Because the app
is installed per-user (in %LOCALAPPDATA%) no elevation/UAC is needed.

No third-party dependencies: only the Python standard library, so nothing new
to bundle into the PyInstaller build.
"""

import os
import ssl
import sys
import json
import tempfile
import threading
import subprocess
import urllib.request

from PyQt6.QtCore import QObject, pyqtSignal

from version import __version__

# --- Repository / release configuration -----------------------------------

GITHUB_OWNER = "doubletaponair"
GITHUB_REPO = "QAudioPlayer"
API_LATEST = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
# The release asset the updater downloads. Keep this in sync with build.bat's
# --name and the file you attach to each GitHub release.
ASSET_NAME = "QAudioPlayer.exe"

_USER_AGENT = f"QAudioPlayer-Updater/{__version__}"


# --- Pure helpers (no Qt, easy to test) ------------------------------------

def current_version():
    return __version__


def _parse_version(text):
    """Turn 'v1.2.3' / '1.2' / '1.2.3-beta' into a comparable (1, 2, 3) tuple."""
    text = (text or "").strip().lstrip("vV")
    parts = []
    for chunk in text.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer(latest, current):
    """True if version string `latest` is strictly newer than `current`."""
    return _parse_version(latest) > _parse_version(current)


def fetch_latest_release(timeout=10):
    """Return (tag_name, asset_download_url|None) for the latest release."""
    req = urllib.request.Request(
        API_LATEST,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": _USER_AGENT,
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        data = json.load(resp)
    tag = data.get("tag_name", "") or ""
    url = None
    for asset in data.get("assets", []):
        if asset.get("name") == ASSET_NAME:
            url = asset.get("browser_download_url")
            break
    return tag, url


def check_for_update():
    """Return (available, latest_version, download_url).

    `available` is True only when the latest release is newer than the running
    version AND it carries the expected exe asset.
    """
    tag, url = fetch_latest_release()
    if not tag:
        return (False, current_version(), None)
    available = is_newer(tag, current_version()) and url is not None
    return (available, tag.lstrip("vV"), url)


def download_update(url, dest_path, progress_cb=None, timeout=120):
    """Stream the asset at `url` to `dest_path`, calling progress_cb(done,total)."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        total = int(resp.headers.get("Content-Length", 0) or 0)
        done = 0
        with open(dest_path, "wb") as fh:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                if progress_cb:
                    progress_cb(done, total)


def apply_update_and_restart(new_exe_path):
    """Swap the running exe for `new_exe_path` and relaunch (Windows only).

    A running .exe can't overwrite itself, so we spawn a detached batch file
    that waits for this PID to exit, moves the new file into place, then
    starts it again. The caller should quit the app immediately after.
    """
    if not getattr(sys, "frozen", False):
        raise RuntimeError(
            "Updates can only be applied to the built executable, "
            "not when running from source."
        )

    target = sys.executable          # the running QAudioPlayer.exe
    pid = os.getpid()
    bat_path = os.path.join(tempfile.gettempdir(), "qaudioplayer_update.bat")

    script = (
        "@echo off\r\n"
        ":wait\r\n"
        f'tasklist /FI "PID eq {pid}" /NH 2>nul | find "{pid}" >nul\r\n'
        "if not errorlevel 1 (\r\n"
        "  timeout /t 1 /nobreak >nul\r\n"
        "  goto wait\r\n"
        ")\r\n"
        f'move /Y "{new_exe_path}" "{target}" >nul\r\n'
        f'start "" "{target}"\r\n'
        'del "%~f0"\r\n'
    )
    with open(bat_path, "w") as fh:
        fh.write(script)

    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )


# --- Qt-friendly manager ----------------------------------------------------

class UpdateManager(QObject):
    """Runs network work off the UI thread and reports back via signals."""

    updateAvailable = pyqtSignal(str, str)    # latest_version, download_url
    upToDate = pyqtSignal(str)                 # current_version
    checkFailed = pyqtSignal(str)              # error message
    downloadProgress = pyqtSignal(int, int)    # bytes_done, bytes_total
    downloadFailed = pyqtSignal(str)           # error message
    readyToRestart = pyqtSignal(str)           # path to downloaded exe

    def check_async(self):
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self):
        try:
            available, latest, url = check_for_update()
        except Exception as exc:  # offline, rate-limited, no release yet, etc.
            self.checkFailed.emit(str(exc))
            return
        if available:
            self.updateAvailable.emit(latest, url)
        else:
            self.upToDate.emit(current_version())

    def download_and_apply_async(self, url):
        threading.Thread(
            target=self._download, args=(url,), daemon=True
        ).start()

    def _download(self, url):
        try:
            if not getattr(sys, "frozen", False):
                self.downloadFailed.emit(
                    "Updates can only be installed in the built app, "
                    "not when running from source."
                )
                return
            target_dir = os.path.dirname(sys.executable)
            new_path = os.path.join(target_dir, "QAudioPlayer.new.exe")
            download_update(
                url,
                new_path,
                progress_cb=lambda d, t: self.downloadProgress.emit(d, t),
            )
            self.readyToRestart.emit(new_path)
        except Exception as exc:
            self.downloadFailed.emit(str(exc))
