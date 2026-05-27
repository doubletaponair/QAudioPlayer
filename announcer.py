"""
Announcer - speaks messages through the active screen reader.

Tries three paths in order, first-success-wins:

1. NVDA Controller Client (nvdaControllerClient64.dll)
   The most reliable path for NVDA users. We search the app folder, the
   current working directory, PyInstaller's _MEIPASS extraction folder,
   standard NVDA install locations, and the system PATH.

2. Qt accessibility announcements (Qt 6.8+)
   Only available when PyQt6's QAccessible is exposed. Python 3.14 wheels
   currently do not expose it; Python 3.13 wheels do.

3. Status label fallback (handled by main_window)
   Silent, but the on-screen label is still updated.
"""

import os
import sys
import ctypes
from pathlib import Path

from PyQt6.QtCore import QObject, QT_VERSION_STR

# --------------------------------------------------------------------------
# Path 1: NVDA Controller Client
# --------------------------------------------------------------------------

_nvda_dll = None
_nvda_dll_path = None
_nvda_load_attempted = False


def _nvda_search_paths():
    """Return a list of folders to search for nvdaControllerClient64.dll."""
    paths = []

    # 1. Same folder as the running script / frozen exe.
    if getattr(sys, "frozen", False):
        paths.append(Path(sys.executable).parent)
        # PyInstaller --onefile extracts bundled binaries to sys._MEIPASS.
        # When build.bat uses --add-binary the DLL lands there.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            paths.append(Path(meipass))
    else:
        paths.append(Path(__file__).resolve().parent)

    # 2. Current working directory.
    paths.append(Path.cwd())

    # 3. Standard NVDA install locations.
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    app_data = os.environ.get("APPDATA", "")

    for base in (program_files_x86, program_files):
        if base:
            paths.append(Path(base) / "NVDA")

    for base in (local_app_data, app_data):
        if base:
            paths.append(Path(base) / "nvda")

    # 4. NVDA install location from the registry (Windows only).
    if sys.platform.startswith("win"):
        try:
            import winreg
            registry_locations = [
                (winreg.HKEY_LOCAL_MACHINE,
                 r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\NVDA"),
                (winreg.HKEY_LOCAL_MACHINE,
                 r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\NVDA"),
                (winreg.HKEY_CURRENT_USER,
                 r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\NVDA"),
            ]
            for hive, subkey in registry_locations:
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        for value_name in ("InstallLocation", "UninstallDirectory"):
                            try:
                                install_dir, _ = winreg.QueryValueEx(key, value_name)
                                if install_dir:
                                    paths.append(Path(install_dir))
                            except FileNotFoundError:
                                continue
                except OSError:
                    continue
        except ImportError:
            pass

    return paths


def _try_load_nvda():
    global _nvda_dll, _nvda_dll_path, _nvda_load_attempted
    if _nvda_load_attempted:
        return _nvda_dll
    _nvda_load_attempted = True

    if not sys.platform.startswith("win"):
        return None

    dll_name = "nvdaControllerClient64.dll"

    candidates = []
    for folder in _nvda_search_paths():
        candidates.append(folder / dll_name)
        candidates.append(folder / "x64" / dll_name)
        candidates.append(folder / "controllerClient" / dll_name)
        candidates.append(folder / "controllerClient" / "x64" / dll_name)

    for candidate in candidates:
        if candidate.exists():
            try:
                dll = ctypes.windll.LoadLibrary(str(candidate))
                dll.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                dll.nvdaController_speakText.restype = ctypes.c_ulong
                try:
                    dll.nvdaController_cancelSpeech.argtypes = []
                    dll.nvdaController_cancelSpeech.restype = ctypes.c_ulong
                except AttributeError:
                    pass
                _nvda_dll = dll
                _nvda_dll_path = str(candidate)
                return _nvda_dll
            except Exception:
                continue

    # Last-ditch: let Windows resolve from PATH.
    try:
        dll = ctypes.windll.LoadLibrary(dll_name)
        dll.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
        dll.nvdaController_speakText.restype = ctypes.c_ulong
        _nvda_dll = dll
        _nvda_dll_path = dll_name + " (via system PATH)"
    except Exception:
        _nvda_dll = None

    return _nvda_dll


# --------------------------------------------------------------------------
# Path 2: Qt accessibility announcements
# --------------------------------------------------------------------------

HAS_QACCESSIBLE = False
HAS_ANNOUNCEMENT_EVENT = False
QAccessible = None
QAccessibleAnnouncementEvent = None

try:
    from PyQt6.QtGui import QAccessible as _QAccessibleCls
    QAccessible = _QAccessibleCls
    HAS_QACCESSIBLE = True
except ImportError:
    pass

if HAS_QACCESSIBLE:
    try:
        from PyQt6.QtGui import QAccessibleAnnouncementEvent as _AnnEvt
        QAccessibleAnnouncementEvent = _AnnEvt
        HAS_ANNOUNCEMENT_EVENT = True
    except ImportError:
        pass


# --------------------------------------------------------------------------
# Announcer class
# --------------------------------------------------------------------------

class Announcer(QObject):
    def __init__(self, target_widget):
        super().__init__(target_widget)
        self._target = target_widget
        _try_load_nvda()

    @property
    def qt_version(self):
        return QT_VERSION_STR

    @property
    def available_methods(self):
        methods = []
        if _nvda_dll is not None:
            methods.append("NVDA Controller Client")
        if HAS_ANNOUNCEMENT_EVENT:
            methods.append("Qt Accessibility")
        if not methods:
            methods.append("status label only")
        return methods

    @property
    def nvda_dll_path(self):
        return _nvda_dll_path

    def announce(self, message, assertive=False):
        if not message:
            return False

        # Path 1: NVDA Controller Client.
        if _nvda_dll is not None:
            try:
                if assertive:
                    try:
                        _nvda_dll.nvdaController_cancelSpeech()
                    except Exception:
                        pass
                result = _nvda_dll.nvdaController_speakText(
                    ctypes.c_wchar_p(message)
                )
                if result == 0:
                    return True
            except Exception:
                pass

        # Path 2: Qt accessibility event.
        if HAS_ANNOUNCEMENT_EVENT and self._target is not None:
            try:
                event = QAccessibleAnnouncementEvent(self._target, message)
                try:
                    priority_enum = QAccessible.AnnouncementPriority
                    priority = (
                        priority_enum.Assertive if assertive else priority_enum.Polite
                    )
                    event.setPriority(priority)
                except (AttributeError, TypeError):
                    pass
                QAccessible.updateAccessibility(event)
                return True
            except Exception:
                pass

        # Path 3: caller (main_window) updates the status label.
        return False
