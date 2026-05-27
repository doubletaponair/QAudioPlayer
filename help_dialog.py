"""
Help dialog - minimal, screen-reader friendly list of keyboard shortcuts.

Implementation: a QListWidget with TWO items per shortcut - the key on
one item, the action on the next. NVDA reads each item as you arrow
up/down, giving the exact behaviour the user asked for:

    [arrow] "L"
    [arrow] "Play forward (press again to cycle 1x, 2x, 3x)"
    [arrow] "K"
    [arrow] "Pause"
    ...

Avoids QTableWidget's "data item, row 1, column 2" announcements and
QPlainTextEdit's internal cursor navigation which NVDA doesn't follow
reliably.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
)


SHORTCUTS = [
    ("L", "Play forward (press again to cycle 1x, 2x, 3x)"),
    ("K", "Pause"),
    ("J", "Rewind (press again to cycle 1x, 2x, 3x)"),
    ("Spacebar", "Toggle play and pause"),
    ("Left arrow", "Jump backward 5 seconds"),
    ("Right arrow", "Jump forward 5 seconds"),
    ("Shift + Left arrow", "Jump backward 30 seconds"),
    ("Shift + Right arrow", "Jump forward 30 seconds"),
    ("Home", "Jump to start of file"),
    ("End", "Jump to end of file"),
    ("0 to 9", "Jump to 0, 10, 20 through 90 percent of the file"),
    ("Up arrow", "Volume up"),
    ("Down arrow", "Volume down"),
    ("M", "Toggle mute"),
    ("V", "Speak current volume and mute state"),
    ("R", "Speak remaining time"),
    ("T", "Speak elapsed and total time"),
    ("O or Ctrl + O", "Open a file"),
    ("F1, H, or Ctrl + slash", "Show this help window"),
    ("Escape", "Close this help window"),
]


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard shortcuts")
        self.setModal(True)
        self.resize(520, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._list = QListWidget(self)
        self._list.setWordWrap(True)
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        for key, action in SHORTCUTS:
            self._list.addItem(QListWidgetItem(key))
            self._list.addItem(QListWidgetItem(action))

        # Select the first row so NVDA reads "L" when the dialog appears.
        self._list.setCurrentRow(0)
        layout.addWidget(self._list, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.clicked.connect(self.accept)
        layout.addWidget(buttons)

        # Escape closes the dialog.
        esc = QShortcut(QKeySequence("Escape"), self)
        esc.activated.connect(self.accept)

        # Focus the list so arrow keys work immediately.
        self._list.setFocus()
