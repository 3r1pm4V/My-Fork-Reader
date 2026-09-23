from PyQt6.QtWidgets import QApplication

THEMES = {
    'light': """
        QMainWindow, QWidget {
            background-color: #ffffff;
            color: #2c3e50;
        }
        QToolBar {
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            spacing: 10px;
            padding: 5px;
        }
        QStatusBar {
            background-color: #f8f9fa;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }
        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #dee2e6;
        }
        QMenuBar::item:selected {
            background-color: #e9ecef;
        }
    """,
    'dark': """
        QMainWindow, QWidget {
            background-color: #1a1a1a;
            color: #e0e0e0;
        }
        QToolBar {
            background-color: #2d2d2d;
            border-bottom: 1px solid #404040;
            spacing: 10px;
            padding: 5px;
        }
        QStatusBar {
            background-color: #2d2d2d;
            color: #a0a0a0;
            border-top: 1px solid #404040;
        }
        QMenuBar {
            background-color: #1a1a1a;
            color: #e0e0e0;
            border-bottom: 1px solid #404040;
        }
        QMenuBar::item:selected {
            background-color: #3d3d3d;
        }
        QPushButton {
            background-color: #3d3d3d;
            color: white;
            border: 1px solid #555;
            padding: 5px;
        }
    """,
    'sepia': """
        QMainWindow, QWidget {
            background-color: #f4ecd8;
            color: #5b4636;
        }
        QToolBar {
            background-color: #eaddc0;
            border-bottom: 1px solid #d3c4a9;
            spacing: 10px;
            padding: 5px;
        }
        QStatusBar {
            background-color: #eaddc0;
            color: #5b4636;
            border-top: 1px solid #d3c4a9;
        }
        QMenuBar {
            background-color: #f4ecd8;
            color: #5b4636;
            border-bottom: 1px solid #d3c4a9;
        }
    """
}

def apply_theme(app: QApplication, name: str):
    """
    Applies a theme to the entire application.
    
    Args:
        app: The QApplication instance.
        name: Theme name ('light', 'dark', 'sepia').
    """
    qss = THEMES.get(name.lower(), THEMES['light'])
    app.setStyleSheet(qss)

# TODO / EXTENSION POINTS:
# 1. Add support for custom user-defined CSS themes.
# 2. Implement dynamic font injection into the QSS.
# 3. Add high-contrast accessibility themes.
# 4. Support for OS-level light/dark mode auto-switching.
