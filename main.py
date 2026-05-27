"""
QAudioPlayer - Entry point.

A keyboard-first, screen-reader-friendly media player for Windows,
inspired by QuickTime's JKL controls.
"""

import sys
import os
import traceback

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox


def main():
    from version import __version__

    app = QApplication(sys.argv)
    app.setApplicationName("QAudioPlayer")
    app.setApplicationDisplayName("QAudioPlayer")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("QAudioPlayer")

    try:
        from main_window import MainWindow
    except Exception as e:
        QMessageBox.critical(
            None,
            "Startup error",
            f"Failed to import application modules:\n\n{e}\n\n"
            f"Please make sure PyQt6 and python-vlc are installed.\n\n"
            f"{traceback.format_exc()}"
        )
        return 1

    try:
        window = MainWindow()
    except Exception as e:
        QMessageBox.critical(
            None,
            "Startup error",
            f"Failed to start the media engine.\n\n"
            f"Please make sure VLC media player is installed (64-bit) "
            f"from https://www.videolan.org/vlc/\n\n"
            f"Technical details:\n{e}"
        )
        return 1

    window.show()

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if os.path.isfile(filepath):
            window.open_file(filepath)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
