from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtGui import QAction

def register(main_window):
    """
    Standard entry point for E-Reader plugins.
    Adds a menu item to the main window.
    """
    # Find or create Plugins menu
    menubar = main_window.menuBar()
    
    # Check if Plugins menu already exists
    plugins_menu = None
    for action in menubar.actions():
        if action.text() == "&Plugins":
            plugins_menu = action.menu()
            break
            
    if not plugins_menu:
        plugins_menu = menubar.addMenu("&Plugins")

    hello_action = QAction("Say Hello", main_window)
    hello_action.triggered.connect(lambda: QMessageBox.information(main_window, "Hello", "Hello from Plugin!"))
    plugins_menu.addAction(hello_action)
