from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QGridLayout
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QColor, QLinearGradient, QPalette, QBrush, QPainter

class SkeletonItem(QFrame):
    def __init__(self, parent=None, is_circle=False):
        super().__init__(parent)
        self.is_circle = is_circle
        self._gradient_pos = -1.0
        self.setStyleSheet("border-radius: 4px; background-color: #e0e0e0;")
        
    def set_color(self, color_hex: str):
        radius = "50%" if self.is_circle else "4px"
        self.setStyleSheet(f"border-radius: {radius}; background-color: {color_hex};")

    @pyqtProperty(float)
    def gradient_pos(self) -> float:
        return self._gradient_pos

    @gradient_pos.setter
    def gradient_pos(self, pos: float):
        self._gradient_pos = pos
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._gradient_pos <= -1.0 or self._gradient_pos >= 1.0:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        gradient = QLinearGradient(0, 0, self.width(), 0)
        shimmer_color = QColor(255, 255, 255, 80)
        
        pos = self._gradient_pos
        # Ensure positions are within [0, 1] and strictly increasing
        p1 = max(0.0, min(1.0, pos - 0.2))
        p2 = max(0.0, min(1.0, pos))
        p3 = max(0.0, min(1.0, pos + 0.2))
        
        # Avoid duplicate positions which can cause warnings in some Qt versions
        # and ensure they are sorted
        stops = sorted(list(set([p1, p2, p3])))
        
        if len(stops) >= 2:
            if p1 in stops: gradient.setColorAt(p1, QColor(0, 0, 0, 0))
            if p2 in stops: gradient.setColorAt(p2, shimmer_color)
            if p3 in stops: gradient.setColorAt(p3, QColor(0, 0, 0, 0))
        
        painter.fillRect(self.rect(), QBrush(gradient))

class SkeletonLoader(QWidget):
    def __init__(self, parent=None, mode: str = "text"):
        super().__init__(parent)
        self.mode = mode
        self.items: list[SkeletonItem] = []
        self._setup_ui()
        
        self.animation = QPropertyAnimation(self, b"shimmer_val")
        self.animation.setDuration(1500)
        self.animation.setLoopCount(-1)
        self.animation.setStartValue(-1.0)
        self.animation.setEndValue(1.0)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        if self.mode == "text":
            import random
            for _ in range(12):
                item = SkeletonItem()
                item.setFixedHeight(14)
                item.setFixedWidth(random.randint(60, 95) * 4) # Placeholder width
                layout.addWidget(item)
                self.items.append(item)
        elif self.mode == "grid":
            grid = QGridLayout()
            grid.setSpacing(20)
            for i in range(12):
                item = SkeletonItem()
                item.setFixedSize(150, 220)
                grid.addWidget(item, i // 4, i % 4)
                self.items.append(item)
            layout.addLayout(grid)
            
    @pyqtProperty(float)
    def shimmer_val(self) -> float:
        return 0.0

    @shimmer_val.setter
    def shimmer_val(self, value: float):
        for item in self.items:
            item.gradient_pos = value

    def start_animation(self):
        self.animation.start()

    def stop_animation(self):
        self.animation.stop()

    def set_theme(self, theme: str):
        color = "#e0e0e0" if theme == "light" else "#2a2a2a"
        self.setStyleSheet(f"background-color: {'#ffffff' if theme == 'light' else '#1a1a1a'};")
        for item in self.items:
            item.set_color(color)
