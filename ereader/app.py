import logging
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from ereader.config import load_config
from ereader.db import Database
from ereader.logger import setup_logging


from ereader.ui.main_window import MainWindow


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
    # Load config and setup logging
    config = load_config()
    setup_logging(config)
    
    logging.info("Starting E-Reader application...")

    # Initialize Database
    app_dir = Path(config.library.path).expanduser()
    app_dir.mkdir(parents=True, exist_ok=True)
    db_path = app_dir / "library.db"
    db = Database(str(db_path))
    db.connect()

    # Create Application
    app = App(sys.argv)
    
    # Initialize Main Window
    window = MainWindow(config, db)
    window.show()

    try:
        sys.exit(app.exec())
    finally:
        db.close()
        logging.info("Application closed.")


# TODO / EXTENSION POINTS:
# 1. Integrate QSS (Qt Style Sheets) for global theming.
# 2. Implement a splash screen during heavy resource loading (DB init, Config check).
# 3. Add system tray icon for background sync indicators.
# 4. Handle OS-level signals (SIGINT, SIGTERM) for graceful shutdown.
