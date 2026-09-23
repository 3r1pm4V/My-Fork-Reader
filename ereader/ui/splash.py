from PyQt6.QtWidgets import QSplashScreen, QVBoxLayout, QProgressBar, QLabel, QWidget
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtCore import Qt

class SplashScreen(QSplashScreen):
    """
    Custom splash screen with progress bar and skeleton-style shimmer.
    """
    def __init__(self):
        pixmap = QPixmap(400, 300)
        pixmap.fill(QColor("#1a1a1a"))
        super().__init__(pixmap)
        
        # Overlay Skeleton for shimmer effect
        from ereader.ui.skeleton import SkeletonLoader
        self.skeleton = SkeletonLoader(self, mode="text")
        self.skeleton.setGeometry(0, 0, 400, 200)
        self.skeleton.set_theme("dark")
        self.skeleton.start_animation()
        
        # Create layout for child widgets
        self.container = QWidget(self)
        self.container.setGeometry(0, 200, 400, 100)
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(20, 0, 20, 20)
        self.layout.addStretch()
        
        self.label = QLabel("Đang khởi động...")
        self.label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(10)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 5px;
                background-color: #333;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 4px;
            }
        """)
        self.layout.addWidget(self.progress)

    def set_progress(self, value: int, message: str = None):
        self.progress.setValue(value)
        if message:
            self.label.setText(message)
        self.showMessage(message, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)

__all__ = ["SplashScreen"]
