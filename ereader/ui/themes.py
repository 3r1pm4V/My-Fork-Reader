import logging
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject

class ThemeManager(QObject):
    theme_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._current_theme = None
        self._qss_cache = {}

    def get_theme_variables(self, name: str) -> dict:
        if name == "auto":
            name = self.detect_system_theme()
            
        return THEME_VARIABLES.get(name, THEME_VARIABLES['dark'])

    def detect_system_theme(self) -> str:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if value == 1 else "dark"
        except Exception:
            return "dark"

    def apply_theme(self, app: QApplication, name: str):
        start_time = time.perf_counter()
        
        if name == self._current_theme and name != "auto":
            return

        variables = self.get_theme_variables(name)
        
        if name not in self._qss_cache:
            self._qss_cache[name] = QSS_TEMPLATE.format(**variables)
            
        app.setStyleSheet(self._qss_cache[name])
        self._current_theme = name
        self.theme_changed.emit(variables)
        
        duration = (time.perf_counter() - start_time) * 1000
        logging.info(f"Theme '{name}' applied in {duration:.2f} ms")

THEME_VARIABLES = {
    'light': {
        'bg': '#ffffff',
        'fg': '#111111',
        'accent': '#0066ff',
        'surface': '#ffffff',
        'border': '#e0e0e0',
        'selection': '#f0f7ff',
        'scrollbar': '#d0d0d0'
    },
    'dark': {
        'bg': '#121212',
        'fg': '#e0e0e0',
        'accent': '#0066ff',
        'surface': '#1e1e1e',
        'border': '#2c2c2c',
        'selection': '#333333',
        'scrollbar': '#444'
    },
    'sepia': {
        'bg': '#fbf0d9',
        'fg': '#5b4636',
        'accent': '#b8860b',
        'surface': '#fbf0d9',
        'border': '#d8ccb0',
        'selection': '#f0e4c0',
        'scrollbar': '#dcd0b0'
    }
}

QSS_TEMPLATE = """
    QMainWindow, QWidget {{
        background-color: {bg};
        color: {fg};
        font-family: "Segoe UI", sans-serif;
    }}
    QMenuBar {{
        background-color: {bg};
        color: {fg};
        border-bottom: 1px solid {border};
    }}
    QMenuBar::item {{
        background-color: transparent;
        padding: 5px 10px;
    }}
    QMenuBar::item:selected {{
        background-color: {selection};
    }}
    QMenu {{
        background-color: {surface};
        color: {fg};
        border: 1px solid {border};
        padding: 5px;
    }}
    QMenu::item {{
        padding: 8px 25px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {selection};
        color: {accent};
    }}
    QToolBar {{
        background-color: {surface};
        border-bottom: 1px solid {border};
        spacing: 10px;
        padding: 5px;
    }}
    QStatusBar {{
        background-color: {surface};
        color: {fg};
        border-top: 1px solid {border};
    }}
    QLineEdit {{
        border: 1px solid {border};
        border-radius: 6px;
        padding: 6px 10px;
        background: {surface};
        color: {fg};
        selection-background-color: {accent};
        selection-color: white;
    }}
    QLineEdit::placeholder {{
        color: {fg};
        opacity: 0.6;
    }}
    QLineEdit:focus {{
        border: 1px solid {accent};
    }}
    QPushButton {{
        background-color: {surface};
        color: {fg};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 14px;
    }}
    #ReaderHeader QPushButton, #ReaderFooter QPushButton {{
        font-size: 18px;
        padding: 6px 12px;
        border: none;
        background: transparent;
        font-weight: bold;
    }}
    #ReaderHeader QPushButton:hover, #ReaderFooter QPushButton:hover {{
        background-color: {selection};
        border-radius: 4px;
    }}
    QPushButton:hover {{ 
        background-color: {selection}; 
        border-color: {accent};
    }}
    QPushButton:pressed {{
        background-color: {border};
    }}
    #ImportButton {{
        background-color: {accent};
        color: white;
        border: none;
        font-weight: bold;
        font-size: 18px;
    }}
    #ImportButton:hover {{
        background-color: {selection};
        color: {accent};
    }}
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {scrollbar};
        border-radius: 5px;
        min-height: 30px;
        margin: 2px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QTabWidget::pane {{ border: 1px solid {border}; }}
    QTabBar::tab {{
        background: {surface};
        color: {fg};
        padding: 8px 12px;
        border: 1px solid {border};
    }}
    QTabBar::tab:selected {{ background: {bg}; font-weight: bold; }}
    QListView, QTableView {{
        border: none;
        background-color: {bg};
        selection-background-color: {selection};
        selection-color: {fg};
    }}
    #LibraryGrid {{
        background-color: transparent;
    }}
    #LibraryGrid::item {{
        color: {fg};
    }}
    #LibraryGrid::item:selected {{
        background-color: {selection};
        border-radius: 8px;
    }}
    QHeaderView::section {{
        background-color: {surface};
        color: {fg};
        padding: 4px;
        border: 1px solid {border};
    }}
    QProgressBar {{
        background-color: {border};
        border: none;
        border-radius: 2px;
        height: 4px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 2px;
    }}
    QLabel {{
        color: {fg};
        font-size: 13px;
        font-weight: 500;
    }}
    #ReaderHeader, #ReaderFooter {{
        background-color: {bg};
        border-top: 1px solid {border};
        padding: 5px;
    }}
    #ReaderHeader {{
        border-top: none;
        border-bottom: 1px solid {border};
    }}
"""

theme_manager = ThemeManager()

def apply_theme(app: QApplication, name: str):
    """Global convenience function for theme application."""
    theme_manager.apply_theme(app, name)

__all__ = ["ThemeManager", "theme_manager", "apply_theme", "THEME_VARIABLES"]
