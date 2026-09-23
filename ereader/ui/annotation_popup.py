from PyQt6.QtWidgets import QMenu, QInputDialog, QMessageBox
from PyQt6.QtGui import QAction, QColor, QIcon
from PyQt6.QtCore import pyqtSignal


class AnnotationPopup(QMenu):
    """
    Context menu displayed when text is selected in the reader.
    """
    highlight_requested = pyqtSignal(str)  # Color name
    note_requested = pyqtSignal(str)       # Note content
    copy_requested = pyqtSignal()
    remove_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_actions()

    def _setup_actions(self):
        # Highlights
        colors = {
            "Yellow": "#ffff00",
            "Green": "#00ff00",
            "Blue": "#00ffff",
            "Pink": "#ff00ff"
        }
        
        highlight_menu = self.addMenu("Highlight")
        for name, hex_code in colors.items():
            act = QAction(name, self)
            act.triggered.connect(lambda checked, c=hex_code: self.highlight_requested.emit(c))
            highlight_menu.addAction(act)

        # Note
        note_act = self.addAction("Add Note")
        note_act.triggered.connect(self._prompt_note)

        self.addSeparator()

        # Utils
        copy_act = self.addAction("Copy")
        copy_act.triggered.connect(self.copy_requested.emit)

        self.addSeparator()

        remove_act = self.addAction("Remove Annotation")
        remove_act.triggered.connect(self.remove_requested.emit)

    def _prompt_note(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Note", "Enter your note:")
        if ok and text:
            self.note_requested.emit(text)
