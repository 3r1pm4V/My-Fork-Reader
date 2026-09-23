import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PyQt6.QtCore import pyqtSignal, Qt, QUrl

# Try to import WebEngine, fallback to QTextBrowser if not available
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False
    logging.warning("PyQt6-WebEngine not found. Falling back to QTextBrowser for reading.")

from ereader.formats.base import Document


class ReaderView(QWidget):
    """
    Widget responsible for rendering book content.
    Uses QWebEngineView for modern HTML support, or QTextBrowser as fallback.
    """
    
    page_changed = pyqtSignal(int, int)  # current_page, total_pages
    progress_changed = pyqtSignal(float)  # percentage

    def __init__(self, config, db, parent=None):
        super().__init__(parent)
        self.config = config
        self.db = db
        self.document: Optional[Document] = None
        self.current_page_idx = 0
        self.zoom_factor = 1.0
        
        self._init_ui()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        if HAS_WEBENGINE:
            self.viewer = QWebEngineView()
            # Disable context menu for cleaner reading experience
            self.viewer.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        else:
            self.viewer = QTextBrowser()
            self.viewer.setOpenExternalLinks(True)

        self.layout.addWidget(self.viewer)

    def set_document(self, doc: Document):
        """Loads a new document into the viewer."""
        self.document = doc
        self.current_page_idx = 0
        
        # Load last saved progress if available
        # (This assumes the book is already in the 'books' table, 
        # normally handled by the library module in Part 4)
        # For now, we just reset to 0.
        
        self.update_display()

    def update_display(self):
        """Renders the current page of the document."""
        if not self.document:
            return

        page = self.document.get_page(self.current_page_idx)
        content = self.document.get_html() if hasattr(self.document, 'get_html') else page.html
        
        # Inject theme-specific CSS into the HTML content
        styled_html = self._apply_content_styling(content)

        if HAS_WEBENGINE:
            self.viewer.setHtml(styled_html, QUrl.fromLocalFile(str(self.document.path.parent)))
        else:
            self.viewer.setHtml(styled_html)

        # Emit signals
        total = self.document.total_pages
        self.page_changed.emit(self.current_page_idx + 1, total)
        
        progress = ((self.current_page_idx + 1) / total) * 100 if total > 0 else 0
        self.progress_changed.emit(progress)

    def _apply_content_styling(self, html: str) -> str:
        """Injects font and color settings from config into the HTML."""
        theme = self.config.reading.theme
        bg_color = "#ffffff"
        text_color = "#2c3e50"
        
        if theme == 'dark':
            bg_color = "#1a1a1a"
            text_color = "#e0e0e0"
        elif theme == 'sepia':
            bg_color = "#f4ecd8"
            text_color = "#5b4636"

        font_family = self.config.reading.font_family
        font_size = self.config.reading.font_size
        line_height = self.config.reading.line_height

        style = f"""
        <style>
            body {{
                background-color: {bg_color};
                color: {text_color};
                font-family: '{font_family}', sans-serif;
                font-size: {font_size}px;
                line-height: {line_height};
                padding: 2em;
                margin: auto;
                max-width: 800px;
            }}
            img {{ max-width: 100%; height: auto; }}
        </style>
        """
        if "</head>" in html:
            return html.replace("</head>", f"{style}</head>")
        return f"<html><head>{style}</head><body>{html}</body></html>"

    def next_page(self):
        if self.document and self.current_page_idx < self.document.total_pages - 1:
            self.current_page_idx += 1
            self.update_display()

    def prev_page(self):
        if self.document and self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.update_display()

    def set_font_size(self, px: int):
        self.config.reading.font_size = px
        self.update_display()

    def set_theme(self, theme_name: str):
        self.config.reading.theme = theme_name
        self.update_display()

    def save_progress(self):
        """Saves current reading position to the database."""
        if not self.document:
            return
            
        # Logic to find book_id and call db.update_progress
        # This will be fully functional when Part 4 (Library) is implemented.
        logging.info(f"Saving progress for {self.document.title}: Page {self.current_page_idx}")


# TODO / EXTENSION POINTS:
# 1. Implement text selection and highlighting (JS injection for WebEngine).
# 2. Add 'Two-page' spread view for larger screens.
# 3. Implement smooth scrolling mode vs. page-flip mode.
# 4. Add dictionary lookup via popup on word double-click.
