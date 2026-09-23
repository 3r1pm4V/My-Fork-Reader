import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QToolBar, 
    QLabel, QProgressBar, QMenu
)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from ereader.formats import get_parser
from ereader.ui.reader_view import ReaderView
from ereader.ui.themes import apply_theme


class FileLoaderThread(QThread):
    """Worker thread for loading and parsing book files without blocking UI."""
    finished = pyqtSignal(object)  # Emits the Document object
    error = pyqtSignal(str)

    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            parser = get_parser(self.file_path)
            self.finished.emit(parser)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """
    The main application window for E-Reader.
    Handles menus, toolbars, and file management.
    """

    def __init__(self, config, db):
        super().__init__()
        self.config = config
        self.db = db
        
        self.setWindowTitle("E-Reader Python")
        self.resize(config.window.width, config.window.height)
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        
        # Apply initial theme
        apply_theme(self.window().parent(), self.config.reading.theme)

    def _setup_ui(self):
        self.reader = ReaderView(self.config, self.db)
        self.setCentralWidget(self.reader)
        
        # Connect reader signals
        self.reader.page_changed.connect(self._update_page_info)
        self.reader.progress_changed.connect(self._update_progress_bar)

    def _setup_menu(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open Book", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View Menu
        view_menu = menubar.addMenu("&View")
        
        # Theme Submenu
        theme_menu = QMenu("&Theme", self)
        for t in ['Light', 'Dark', 'Sepia']:
            act = QAction(t, self)
            act.triggered.connect(lambda checked, name=t.lower(): self._change_theme(name))
            theme_menu.addAction(act)
        view_menu.addMenu(theme_menu)
        
        view_menu.addSeparator()
        
        fs_action = QAction("&Fullscreen", self)
        fs_action.setShortcut("F11")
        fs_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fs_action)

    def _setup_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        
        # Navigation
        self.toolbar.addAction("Prev", self.reader.prev_page)
        self.toolbar.addAction("Next", self.reader.next_page)
        
        self.toolbar.addSeparator()
        
        # Font sizing
        self.toolbar.addAction("A-", lambda: self.reader.set_font_size(self.config.reading.font_size - 1))
        self.toolbar.addAction("A+", lambda: self.reader.set_font_size(self.config.reading.font_size + 1))

    def _setup_statusbar(self):
        self.status = self.statusBar()
        
        self.page_label = QLabel("No book loaded")
        self.status.addPermanentWidget(self.page_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        self.status.addPermanentWidget(self.progress_bar)

    def _update_page_info(self, current, total):
        self.page_label.setText(f"Page {current} of {total}")

    def _update_progress_bar(self, percentage):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(int(percentage))

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open eBook", "", 
            "All Books (*.epub *.txt *.fb2 *.html *.htm *.mobi *.azw3);;EPUB (*.epub);;Text (*.txt);;MOBI (*.mobi)"
        )
        if file_path:
            self.load_book(Path(file_path))

    def load_book(self, path: Path):
        self.status.showMessage(f"Loading {path.name}...")
        
        self.loader = FileLoaderThread(path)
        self.loader.finished.connect(self._on_book_loaded)
        self.loader.error.connect(self._on_load_error)
        self.loader.start()

    def _on_book_loaded(self, doc):
        self.reader.set_document(doc)
        self.setWindowTitle(f"{doc.title} - {doc.author} - E-Reader")
        self.status.showMessage("Book loaded successfully.", 3000)

    def _on_load_error(self, msg):
        QMessageBox.critical(self, "Error", f"Could not open book:\n{msg}")
        self.status.clearMessage()

    def _change_theme(self, name):
        apply_theme(self.window().parent(), name)
        self.reader.set_theme(name)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def closeEvent(self, event):
        self.reader.save_progress()
        super().closeEvent(event)


# TODO / EXTENSION POINTS:
# 1. Add 'Recent Files' list to the File menu.
# 2. Implement a Library view toggle (Switch between Grid and Reader).
# 3. Add drag-and-drop support for opening files.
# 4. Integrate system tray notifications for long-running tasks.
