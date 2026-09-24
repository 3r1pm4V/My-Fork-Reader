import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QStackedWidget,
    QWidget, QVBoxLayout, QApplication
)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal

from ereader.concurrency import main_thread_only
from ereader.formats import get_parser
# from ereader.ui.reader_view import ReaderView  <-- Lazy loaded
from ereader.ui.library_view import LibraryView
from ereader.ui.themes import apply_theme
from ereader.ui.settings_dialog import SettingsDialog
from ereader.ui.sync_dialog import SyncDialog
from ereader.features.tts import TTSEngine
from ereader.features.sync import SyncClient, partial_md5, plan_remote_jump
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
        self.scan_runners = []  # Keep references to prevent premature GC

        # --- Sync state (one "session" per opened book) ---
        # Pushes to the server are blocked until (1) the book is really open in
        # the reader AND (2) remote progress has been pulled and reconciled.
        self.sync_runners = []          # keep pull threads alive until finished
        self._sync_generation = 0       # bumped per book, discards stale async results
        self._book_session_open = False
        self._reader_ready = False
        self._remote_done = False
        self._remote_progress = None
        self._reconcile_started = False
        self._sync_ready = False
        self._pending_push = None       # (doc_hash, fraction, cfi)
        self._push_timer = QTimer(self)
        self._push_timer.setSingleShot(True)
        self._push_timer.setInterval(3000)
        self._push_timer.timeout.connect(self._flush_push)
        
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
            self.reader.book_ready.connect(self._on_reader_ready)
            
            # Button connections
            # self.reader.btn_tts.clicked.connect(self._toggle_tts)
            # self.reader.btn_bookmark.clicked.connect(self._add_bookmark)
            
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
        # Leaving the book: send the last position, and ignore late sync results.
        self._flush_push()
        self._book_session_open = False
        self._sync_ready = False
        self._sync_generation += 1
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
                    
                    # Manage lifecycle to prevent GC
                    self.scan_runners.append(runner)
                    
                    runner.finished_task.connect(lambda: self.library_view.refresh_library())
                    runner.finished.connect(lambda: self._cleanup_runner(runner))
                    runner.start()

    def _cleanup_runner(self, runner):
        if runner in self.scan_runners:
            self.scan_runners.remove(runner)

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
        # Switching books: don't lose the previous book's pending position.
        self._flush_push()

        # New sync session. Nothing is pushed until _try_reconcile() has run.
        self._sync_generation += 1
        gen = self._sync_generation
        self._book_session_open = True
        self._sync_ready = False
        self._reader_ready = False
        self._reconcile_started = False
        self._remote_progress = None
        self._remote_done = not self.config.sync.enabled

        # Use partial_md5 as required by KOReader sync protocol
        self.current_doc_hash = partial_md5(doc.path)

        # set_document() only *starts* loading foliate-js in the WebView; the
        # position is not known until the reader emits book_ready.
        self.ensure_reader().set_document(doc, self.current_book_id)
        self.setWindowTitle(f"{doc.title} - E-Reader")
        self.show_reader()

        # Pull remote progress in the background (used to block the UI thread).
        if self.config.sync.enabled:
            self._start_remote_pull(gen, self.current_doc_hash)

    def _start_remote_pull(self, gen: int, doc_hash: str):
        from ereader.concurrency import TaskRunner

        runner = TaskRunner("Sync pull", self.sync_client.pull_progress, doc_hash)
        self.sync_runners.append(runner)
        runner.finished_task.connect(lambda name, data, g=gen: self._on_remote_pulled(g, data))
        runner.failed_task.connect(lambda name, msg, g=gen: self._on_remote_pulled(g, None))
        runner.finished.connect(lambda r=runner: self.sync_runners.remove(r) if r in self.sync_runners else None)
        runner.start()

    @main_thread_only
    def _on_remote_pulled(self, gen: int, data):
        if gen != self._sync_generation:
            return  # user already switched book / went back to the library
        self._remote_progress = data
        self._remote_done = True
        self._try_reconcile()

    @main_thread_only
    def _on_reader_ready(self):
        self._reader_ready = True
        self._try_reconcile()

    def _try_reconcile(self):
        """Runs once per book, when BOTH the reader and the remote pull are done."""
        if not (self._book_session_open and self._reader_ready and self._remote_done):
            return
        if self._reconcile_started:
            return
        self._reconcile_started = True  # set first: the dialog below spins a nested event loop

        remote, self._remote_progress = self._remote_progress, None
        local_percent = self.reader.get_progress_data().get('fraction', 0.0)
        jump = plan_remote_jump(remote, local_percent) if self.config.sync.enabled else None
        logging.debug(f"Sync check: local={local_percent:.4f}, remote={remote}, jump={jump}")

        if jump:
            device = jump.device or "another device"
            reply = QMessageBox.question(
                self, "Sync Conflict",
                f"{device} is at {jump.percentage*100:.1f}% "
                f"(here: {local_percent*100:.1f}%). Jump to it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes and self._book_session_open:
                if jump.cfi:
                    self.reader.go_to_cfi(jump.cfi)
                else:
                    # Remote 'progress' is not an EPUB CFI (e.g. KOReader xpointer)
                    self.reader.go_to_percentage(jump.percentage)

        # From now on page turns are pushed to the server.
        if self._book_session_open:
            self._sync_ready = True

    def _flush_push(self):
        """Send the most recent pending position (async, non-blocking)."""
        self._push_timer.stop()
        if not self._pending_push:
            return
        doc_hash, fraction, cfi = self._pending_push
        self._pending_push = None
        if not self.config.sync.enabled:
            return
        from ereader.concurrency import get_async_runner
        get_async_runner().submit(self.sync_client.push_progress_async(doc_hash, fraction, cfi))

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
        progress_data = self.reader.get_progress_data() if self.reader else {"fraction": 0.0, "cfi": ""}
        fraction = progress_data.get('fraction', current / total if total > 0 else 0)
        cfi = progress_data.get('cfi', f"{current}#0")

        # Local DB update via debouncer
        if self.current_book_id:
            self.progress_debouncer.update(self.current_book_id, fraction, cfi, current - 1)
            
        # Sync update (remote). Debounced: rapid page turns would otherwise fire
        # one PUT each, and concurrent PUTs can land out of order on the server.
        if self.config.sync.enabled and self.current_doc_hash and self._sync_ready:
            self._pending_push = (self.current_doc_hash, fraction, cfi)
            self._push_timer.start()  # restarts the 3s countdown

    def _toggle_tts(self):
        # Simple toggle for now
        pass

    def _add_bookmark(self):
        if not self.current_book_id or not self.reader:
            return
        
        from ereader.models import Bookmark
        import time
        
        page_num = self.reader._current_page + 1
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
            if event.key() == Qt.Key.Key_Left:
                self.reader.prev_page()
            elif event.key() == Qt.Key.Key_Right:
                self.reader.next_page()
        
        if event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.stack.currentIndex() == 1 and self.reader:
            self.reader.save_progress()
            self.reader.end_session()
        # The async loop is about to be torn down, so send the last position
        # synchronously (short timeout) instead of queueing it.
        self._push_timer.stop()
        if self._pending_push and self.config.sync.enabled:
            doc_hash, fraction, cfi = self._pending_push
            self._pending_push = None
            self.sync_client.push_progress(doc_hash, fraction, cfi)
        super().closeEvent(event)
