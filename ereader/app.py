import logging
import sys
import time
from pathlib import Path

# Fix: QtWebEngineWidgets must be imported before QCoreApplication/QApplication instance is created
# or AA_ShareOpenGLContexts must be set.
try:
    from PyQt6 import QtWebEngineWidgets
except ImportError:
    pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QCoreApplication

from ereader.config import load_config
from ereader.db import Database
from ereader.logger import setup_logging


class App(QApplication):
    """
    Custom QApplication class to manage application-wide resources and theming.
    """
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        self.setApplicationName("E-Reader Python")
        self.setOrganizationName("E-Reader-Project")


def run():
    """
    Bootstrap and run the application.
    """
    # Set global attributes before creating QApplication
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    
    start_time = time.perf_counter()
    
    # Create Application first to show Splash Screen IMMEDIATELY
    app = App(sys.argv)
    
    # Show Splash Screen
    from ereader.ui.splash import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    
    splash.set_progress(10, "Đang tải cấu hình...")
    config = load_config()
    setup_logging(config)
    
    splash.set_progress(30, "Đang kết nối cơ sở dữ liệu...")
    # Initialize Database
    app_dir = Path(config.library.path).expanduser()
    app_dir.mkdir(parents=True, exist_ok=True)
    db_path = app_dir / "library.db"
    db = Database(str(db_path))
    db.connect()

    splash.set_progress(60, "Đang chuẩn bị giao diện...")
    # Lazy import MainWindow to save startup time
    from ereader.ui.main_window import MainWindow
    
    window = MainWindow(config, db)
    
    splash.set_progress(90, "Hoàn tất!")
    window.show()
    splash.finish(window)

    # Cache Management
    if config.cache.clear_on_startup:
        logging.info("Clearing cache on startup as per config.")
        db.clear_all_cache()
    
    # Delayed cleanup after 30s
    from PyQt6.QtCore import QTimer
    def run_cleanup():
        max_bytes = config.cache.max_size_mb * 1024 * 1024
        current_bytes = db.cache_size_bytes()
        if current_bytes > max_bytes:
            logging.info(f"Cache size ({current_bytes/1024/1024:.2f} MB) exceeds limit. Cleaning up...")
            target = int(max_bytes * 0.8)
            db.cleanup_oldest_cache(target)
            new_size = db.cache_size_bytes()
            logging.info(f"Cache cleanup finished. New size: {new_size/1024/1024:.2f} MB")
            db.vacuum()

    QTimer.singleShot(30000, run_cleanup)
    
    end_time = time.perf_counter()
    startup_duration = end_time - start_time
    logging.info(f"App started in {startup_duration:.2f}s")
    
    # Measure Library load time
    lib_start = time.perf_counter()
    books_count = len(db.list_books())
    lib_end = time.perf_counter()
    logging.info(f"Library loaded in {lib_end - lib_start:.2f}s ({books_count} books)")

    try:
        sys.exit(app.exec())
    finally:
        from ereader.concurrency import get_async_runner
        runner = get_async_runner()
        if runner:
            runner.stop()
            
        from PyQt6.QtCore import QThreadPool
        QThreadPool.globalInstance().waitForDone(5000)
        
        db.close()
        logging.info("Application closed.")
