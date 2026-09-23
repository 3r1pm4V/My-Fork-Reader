import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QStackedWidget,
    QWidget, QVBoxLayout, QApplication
)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from ereader.concurrency import main_thread_only
from ereader.formats import get_parser
# from ereader.ui.reader_view import ReaderView  <-- Lazy loaded
from ereader.ui.library_view import LibraryView
from ereader.ui.themes import apply_theme
from ereader.ui.settings_dialog import SettingsDialog
from ereader.ui.sync_dialog import SyncDialog
from ereader.features.tts import TTSEngine
from ereader.features.sync import SyncClient, partial_md5
from ereader.features.plugin_loader import PluginLoader


from ereader.features.progress import ProgressDebouncer


class MainWindow(QMainWindow):
    """
    Main application window inspired by Readest.
    Manages switching between Library and Reader views.
    """

    def __init__(self, config, db):
        super().__init__()
        self.config = config
        self.db = db
        self.tts = TTSEngine(config)
        self.sync_client = SyncClient(config)
        self.progress_debouncer = ProgressDebouncer(db)
        self.current_book_id = None
        self.current_doc_hash = ""
        
        self.setWindowTitle("E-Reader")
        self.resize(config.window.width, config.window.height)
        
        self.reader = None  # Lazy loaded
        self._setup_ui()
        self._setup_menu()
        self._load_plugins()
        self._auto_scan()
        
        # Initial theme
        apply_theme(QApplication.instance(), self.config.reading.theme)

    def _setup_ui(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Library View
        self.library_view = LibraryView(self.config, self.db)
        self.library_view.book_opened.connect(self._on_book_opened)
        self.stack.addWidget(self.library_view)
        
        # Reader View will be added to stack on demand in ensure_reader()

    def ensure_reader(self):
        if self.reader is None:
            from ereader.ui.reader_view import ReaderView
            self.reader = ReaderView(self.config, self.db)
            self.reader.back_requested.connect(self.show_library)
            self.reader.page_changed.connect(self._on_page_changed)
            
            # Button connections
            self.reader.btn_tts.clicked.connect(self._toggle_tts)
            self.reader.btn_bookmark.clicked.connect(self._add_bookmark)
            
            self.stack.addWidget(self.reader)
        return self.reader

    def _setup_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("Library", self.show_library)
        file_menu.addAction("Import Book...", self.library_view._on_import_clicked)
        file_menu.addSeparator()
        file_menu.addAction("Settings", self.open_settings)
        exit_action = file_menu.addAction("Exit", self.close)
        exit_action.setShortcut("Ctrl+Q")

        view_menu = menubar.addMenu("&View")
        self.fs_action = QAction("Fullscreen", self, shortcut="F11")
        self.fs_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(self.fs_action)

        theme_menu = view_menu.addMenu("Theme")
        for t in ["Light", "Dark", "Sepia"]:
            act = QAction(t, self)
            act.triggered.connect(lambda ch, n=t.lower(): self._change_theme(n))
            theme_menu.addAction(act)

    def _load_plugins(self):
        plugins_dir = Path(__file__).parent.parent / "plugins"
        PluginLoader.load_all(plugins_dir, self)

    @main_thread_only
    def show_library(self):
        self.stack.setCurrentIndex(0)
        self.setWindowTitle("Library - E-Reader")
        self.library_view.refresh_library()

    @main_thread_only
    def show_reader(self):
        self.stack.setCurrentIndex(1)
        self.ensure_reader().setFocus()

    def _auto_scan(self):
        if self.config.library.auto_scan and self.config.library.folders:
            from ereader.library import scan_folder
            from ereader.concurrency import TaskRunner
            
            for folder_path in self.config.library.folders:
                p = Path(folder_path)
                if p.exists():
                    logging.info(f"Auto-scanning folder: {p}")
                    runner = TaskRunner(f"Auto-scan {p.name}", scan_folder, p, self.db)
                    runner.finished_task.connect(lambda: self.library_view.refresh_library())
                    runner.start()
                    # We don't keep references to runners here for simplicity, 
                    # but in production we might want to track them.

    def _on_book_opened(self, book_id: int, file_path: str):
        self.current_book_id = book_id
        self.load_book(Path(file_path))

    def load_book(self, path: Path):
        # Cancel any previous loader
        if hasattr(self, 'loader') and self.loader and self.loader.isRunning():
            logging.info("Cancelling previous book loader.")
            # QThread doesn't have a built-in 'cancel' that works instantly 
            # for blocking calls, but we can disconnect its signals.
            self.loader.finished_task.disconnect()
            self.loader.failed_task.disconnect()
            self.loader.terminate()
            self.loader.wait()

        from ereader.concurrency import TaskRunner
        self.loader = TaskRunner("Loading Book", get_parser, path, db=self.db)
        self.loader.finished_task.connect(lambda name, doc: self._on_book_loaded(doc))
        self.loader.failed_task.connect(lambda name, m: QMessageBox.critical(self, "Error", m))
        self.loader.start()

    @main_thread_only
    def _on_book_loaded(self, doc):
        self.ensure_reader().set_document(doc, self.current_book_id)
        self.current_doc_hash = partial_md5(doc.path)
        self.setWindowTitle(f"{doc.title} - E-Reader")
        self.show_reader()
        
        # Sync pull
        if self.config.sync.enabled:
            progress = self.sync_client.pull_progress(self.current_doc_hash)
            if progress and 'percentage' in progress:
                # Ask user if they want to apply remote progress
                pass

    def _change_theme(self, name):
        self.config.reading.theme = name
        apply_theme(QApplication.instance(), name)
        if self.reader:
            self.reader.update_display()

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self, new_config):
        self.config = new_config
        self.sync_client = SyncClient(new_config)
        apply_theme(QApplication.instance(), self.config.reading.theme)
        if self.reader:
            self.reader.update_display()

    @main_thread_only
    def _on_page_changed(self, current, total):
        # Local DB update via debouncer
        if self.current_book_id:
            percentage = current / total if total > 0 else 0
            self.progress_debouncer.update(self.current_book_id, percentage, "", current - 1)
        
        # Sync update (remote)
        if self.config.sync.enabled and self.current_doc_hash:
            percentage = current / total if total > 0 else 0
            from ereader.concurrency import get_async_runner
            runner = get_async_runner()
            runner.submit(self.sync_client.push_progress_async(self.current_doc_hash, percentage))

    def _toggle_tts(self):
        # Simple toggle for now
        pass

    def _add_bookmark(self):
        if not self.current_book_id or not self.reader:
            return
        
        from ereader.models import Bookmark
        import time
        
        page_num = self.reader.current_chapter_idx + 1
        bm = Bookmark(
            book_id=self.current_book_id,
            title=f"Chapter {page_num}",
            cfi=str(page_num),
            created_at=int(time.time())
        )
        
        with self.db.transaction() as cursor:
            cursor.execute(
                "INSERT INTO bookmarks (book_id, title, cfi, created_at) VALUES (?, ?, ?, ?)",
                (bm.book_id, bm.title, bm.cfi, bm.created_at)
            )
        
        logging.info(f"Bookmark added for page {page_num}")
        QMessageBox.information(self, "Success", f"Bookmark added for page {page_num}")

    def toggle_fullscreen(self):
        if self.isFullScreen(): self.showNormal()
        else: self.showFullScreen()

    def keyPressEvent(self, event):
        if self.stack.currentIndex() == 1 and self.reader: # Reader
            if event.key() == Qt.Key.Key_S:
                self.reader.btn_sidebar.click()
            elif event.key() == Qt.Key.Key_B and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.reader.btn_bookmark.click()
            elif event.key() == Qt.Key.Key_Left:
                self.reader.prev_page()
            elif event.key() == Qt.Key.Key_Right:
                self.reader.next_page()
            elif event.key() == Qt.Key.Key_T and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.reader.btn_tts.click()
        
        if event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.stack.currentIndex() == 1 and self.reader:
            self.reader.save_progress()
            self.reader.end_session()
        super().closeEvent(event)
