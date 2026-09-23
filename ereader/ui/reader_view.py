import logging
import psutil
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QApplication,
    QLabel, QPushButton, QSplitter, QProgressBar, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt, QUrl, QObject, pyqtSlot, QPropertyAnimation, QEvent
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile

from ereader.formats.base import Document
from ereader.ui.themes import theme_manager
from ereader.ui.skeleton import SkeletonLoader
from ereader.concurrency import main_thread_only

class ReaderBridge(QObject):
    """Bridge for JS -> Python communication only."""
    textSelected = pyqtSignal(str)
    pageCountChanged = pyqtSignal(int)
    navRequested = pyqtSignal(str)

    @pyqtSlot(str)
    def onTextSelected(self, text: str):
        self.textSelected.emit(text)

    @pyqtSlot(int)
    def onPageCountReady(self, count: int):
        self.pageCountChanged.emit(count)
        
    @pyqtSlot(str)
    def onNavRequest(self, direction: str):
        self.navRequested.emit(direction)

class ReaderView(QWidget):
    back_requested = pyqtSignal()
    page_changed = pyqtSignal(int, int) # current, total

    def __init__(self, config, db, parent=None):
        super().__init__(parent)
        self.config = config
        self.db = db
        self.document: Document | None = None
        self.book_id: int | None = None
        
        self.current_chapter_idx = 0
        self.current_column_idx = 0
        self.total_columns = 1
        
        self._bridge = ReaderBridge()
        self._bridge.textSelected.connect(self._on_text_selected)
        self._bridge.pageCountChanged.connect(self._on_page_count_changed)
        self._bridge.navRequested.connect(self._on_nav_requested)
        
        self._setup_ui()
        theme_manager.theme_changed.connect(self._on_theme_changed)
        
        self.viewer.loadFinished.connect(self._on_load_finished)
        self.viewer.installEventFilter(self)

    def _on_nav_requested(self, direction: str):
        if direction == 'next': self.next_page()
        else: self.prev_page()

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Left:
                self.prev_page()
                return True
            elif event.key() == Qt.Key.Key_Right:
                self.next_page()
                return True
        elif event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Ctrl + Scroll to change font size
                delta = event.angleDelta().y()
                if delta > 0:
                    self.config.reading.font_size = min(72, self.config.reading.font_size + 1)
                else:
                    self.config.reading.font_size = max(8, self.config.reading.font_size - 1)
                self.config.save()
                self.update_display()
                return True
        return super().eventFilter(source, event)

    def set_document(self, doc: Document, book_id: int):
        self.document = doc
        self.book_id = book_id
        self.title_label.setText(doc.title)
        
        # Load last progress
        progress = self.db.get_latest_progress(book_id)
        if progress:
            self.current_chapter_idx = progress.get('page_number', 0)
            logging.info(f"Loaded progress for book {book_id}: Chapter {self.current_chapter_idx}")
        else:
            self.current_chapter_idx = 0
            logging.info(f"No progress found for book {book_id}, starting at Chapter 0")
            
        self.current_column_idx = 0
        self.update_display()

    def _on_page_count_changed(self, count: int):
        self.total_columns = max(1, count)
        # If we were waiting to scroll to a specific page (e.g. going back from next chapter)
        if hasattr(self, '_pending_column_idx'):
            self.current_column_idx = self._pending_column_idx
            if self.current_column_idx < 0: 
                self.current_column_idx = self.total_columns - 1
            del self._pending_column_idx
            
        self._apply_scroll()
        self._update_footer()

    def _on_load_finished(self, ok):
        if ok:
            self.viewer.page().runJavaScript("""
                (function() {
                    const count = Math.ceil(document.documentElement.scrollWidth / window.innerWidth);
                    pybridge.onPageCountReady(count);
                })();
            """)

    def _apply_scroll(self):
        js = f"window.scrollTo({self.current_column_idx} * window.innerWidth, 0);"
        self.viewer.page().runJavaScript(js)

    def _update_footer(self):
        if not self.document: return
        total_chapters = self.document.total_pages
        
        # Approximate progress
        chapter_weight = 1.0 / total_chapters if total_chapters > 0 else 0
        column_weight = chapter_weight / self.total_columns if self.total_columns > 0 else 0
        
        progress = (self.current_chapter_idx * chapter_weight) + (self.current_column_idx * column_weight)
        percent = int(progress * 100)
        
        self.progress_bar.setValue(percent)
        self.page_label.setText(f"Chapter {self.current_chapter_idx + 1}/{total_chapters} | Page {self.current_column_idx + 1}/{self.total_columns}")
        self.page_changed.emit(self.current_chapter_idx + 1, total_chapters)

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header
        self.header = QFrame()
        self.header.setObjectName("ReaderHeader")
        self.header.setFixedHeight(50)
        h_layout = QHBoxLayout(self.header)
        self.btn_back = QPushButton("←")
        self.btn_back.clicked.connect(self.back_requested)
        h_layout.addWidget(self.btn_back)
        self.title_label = QLabel("Loading...")
        h_layout.addWidget(self.title_label, 1)
        
        self.btn_sidebar = QPushButton("☰")
        self.btn_sidebar.setToolTip("Table of Contents")
        self.btn_sidebar.clicked.connect(self._show_toc)
        h_layout.addWidget(self.btn_sidebar)
        
        self.btn_bookmark = QPushButton("🔖")
        self.btn_bookmark.setToolTip("Add Bookmark")
        h_layout.addWidget(self.btn_bookmark)
        
        self.btn_tts = QPushButton("🔊")
        self.btn_tts.setToolTip("Text to Speech")
        h_layout.addWidget(self.btn_tts)
        
        self.main_layout.addWidget(self.header)

        # Viewer Container
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        
        # WebEngine Tuning
        profile = QWebEngineProfile("ereader-profile", self)
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        
        self.viewer = QWebEngineView(profile)
        # Register Bridge
        from PyQt6.QtWebChannel import QWebChannel
        self.channel = QWebChannel()
        self.channel.registerObject("pybridge", self._bridge)
        self.viewer.page().setWebChannel(self.channel)
        
        settings = self.viewer.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
        
        self.container_layout.addWidget(self.viewer)
        self.main_layout.addWidget(self.container)

        # Skeleton
        self.skeleton = SkeletonLoader(self.container, mode="text")
        self.skeleton.setVisible(False)

        # Footer
        self.footer = QFrame()
        self.footer.setObjectName("ReaderFooter")
        self.footer.setFixedHeight(50)
        f_layout = QHBoxLayout(self.footer)
        
        self.btn_prev = QPushButton("«")
        self.btn_prev.setToolTip("Previous Chapter")
        self.btn_prev.clicked.connect(self.prev_page)
        f_layout.addWidget(self.btn_prev)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        f_layout.addWidget(self.progress_bar)
        
        self.page_label = QLabel("1/1")
        f_layout.addWidget(self.page_label)
        
        self.btn_next = QPushButton("»")
        self.btn_next.setToolTip("Next Chapter")
        self.btn_next.clicked.connect(self.next_page)
        f_layout.addWidget(self.btn_next)
        
        self.main_layout.addWidget(self.footer)

    @main_thread_only
    def _on_theme_changed(self, vars: dict):
        js = f"""
            if (document.documentElement) {{
                document.documentElement.style.setProperty('--bg', '{vars['bg']}');
                document.documentElement.style.setProperty('--fg', '{vars['fg']}');
                document.documentElement.style.setProperty('--accent', '{vars['accent']}');
            }}
        """
        self.viewer.page().runJavaScript(js)
        self.skeleton.set_theme("light" if vars['bg'] == '#ffffff' else "dark")

    def _on_text_selected(self, text: str):
        logging.info(f"Selected: {text}")

    def _show_toc(self):
        if not self.document or not self.document.toc:
            # Fallback to simple chapter list if TOC is empty
            menu = QMenu(self)
            for i in range(self.document.total_pages):
                act = QAction(f"Chapter {i+1}", self)
                act.triggered.connect(lambda ch, idx=i: self._jump_to_chapter(idx))
                menu.addAction(act)
            menu.exec(self.btn_sidebar.mapToGlobal(self.btn_sidebar.rect().bottomLeft()))
            return

        menu = QMenu(self)
        for item in self.document.toc:
            # Normalize TOC position: remove fragment (#...) and ensure correct path separators
            pos = item.position.split('#')[0].replace('\\', '/')
            
            act = QAction(f"{'  ' * item.level}{item.title}", self)
            
            # Find chapter index by matching normalized position
            target_idx = -1
            for i in range(self.document.total_pages):
                ch = self.document._chapters[i]
                ch_name = ch['name'].replace('\\', '/')
                if pos == ch_name or ch_name.endswith('/' + pos) or pos.endswith('/' + ch_name):
                    target_idx = i
                    break
            
            if target_idx == -1: continue # Skip items we can't map to a chapter
            
            act.triggered.connect(lambda ch, idx=target_idx: self._jump_to_chapter(idx))
            menu.addAction(act)
        
        if menu.isEmpty():
            # If we filtered everything out, show simple chapters
            for i in range(self.document.total_pages):
                act = QAction(f"Chapter {i+1}", self)
                act.triggered.connect(lambda ch, idx=i: self._jump_to_chapter(idx))
                menu.addAction(act)
        
        menu.exec(self.btn_sidebar.mapToGlobal(self.btn_sidebar.rect().bottomLeft()))

    def _jump_to_chapter(self, idx: int):
        self.current_chapter_idx = idx
        self.current_column_idx = 0
        self.update_display()

    def update_display(self):
        if not self.document: return
        total_chapters = self.document.total_pages
        if total_chapters > 0:
            page = self.document.get_page(self.current_chapter_idx)
            vars = theme_manager.get_theme_variables(self.config.reading.theme)
            
            style = f"""
            <style>
                :root {{
                    --bg: {vars['bg']};
                    --fg: {vars['fg']};
                    --accent: {vars['accent']};
                }}
                body {{
                    background-color: var(--bg);
                    color: var(--fg);
                    font-family: '{self.config.reading.font_family}', "Segoe UI", "Georgia", serif;
                    line-height: {self.config.reading.line_height};
                    font-size: {self.config.reading.font_size}px;
                    
                    margin: 0;
                    padding: 0;
                    width: 100vw;
                    height: 100vh;
                    overflow: hidden;
                    
                    /* Single column layout */
                    column-width: 100vw;
                    column-gap: 0;
                    column-fill: auto;
                }}
                .content-wrapper {{
                    padding: 60px 15%;
                    box-sizing: border-box;
                    min-height: 100vh;
                    cursor: pointer;
                }}
                .content-wrapper.image-page {{
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                img, svg {{ 
                    max-width: 100%; 
                    max-height: 85vh; 
                    height: auto; 
                    display: block; 
                    margin: 20px auto; 
                    object-fit: contain;
                    border-radius: 4px;
                }}
                p {{ 
                    margin-bottom: 1.4em; 
                    text-align: justify; 
                    hyphens: auto;
                }}
                h1, h2, h3 {{ 
                    break-before: column; 
                    margin-top: 1.2em; 
                    margin-bottom: 0.8em;
                    color: var(--fg);
                    font-weight: 600;
                    line-height: 1.3;
                }}
            </style>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <script>
                new QWebChannel(qt.webChannelTransport, function (channel) {{
                    window.pybridge = channel.objects.pybridge;
                }});
                
                document.addEventListener('click', function(e) {{
                    const width = window.innerWidth;
                    if (e.clientX < width / 3) {{
                        pybridge.onNavRequest('prev');
                    }} else if (e.clientX > width * 2 / 3) {{
                        pybridge.onNavRequest('next');
                    }}
                }});
            </script>
            """
            content = page.html or page.text
            if not content or content.strip() == "":
                content = f"<div style='text-align: center; margin-top: 40vh; color: var(--fg); font-style: italic;'>[ This chapter appears to be empty or contains only non-text elements ]</div>"
            
            # Detect if this is likely a cover page (mostly just an image)
            is_image_page = "img" in content.lower() and len(page.text.strip()) < 50
            wrapper_class = "content-wrapper image-page" if is_image_page else "content-wrapper"
                
            html = f"<html><head>{style}</head><body><div class='{wrapper_class}'>{content}</div></body></html>"
            self.viewer.setHtml(html)

    def next_page(self):
        if self.current_column_idx < self.total_columns - 1:
            self.current_column_idx += 1
            self._apply_scroll()
            self._update_footer()
        elif self.document and self.current_chapter_idx < self.document.total_pages - 1:
            self.current_chapter_idx += 1
            self.current_column_idx = 0
            self.update_display()

    def prev_page(self):
        if self.current_column_idx > 0:
            self.current_column_idx -= 1
            self._apply_scroll()
            self._update_footer()
        elif self.current_chapter_idx > 0:
            self.current_chapter_idx -= 1
            # We need to scroll to the LAST page of the previous chapter
            self._pending_column_idx = -1 
            self.update_display()

    def save_progress(self):
        if self.document and self.book_id:
            total = self.document.total_pages
            percentage = (self.current_chapter_idx) / total if total > 0 else 0
            self.db.update_progress(
                self.book_id,
                percentage,
                cfi="", # Not implemented yet
                page_num=self.current_chapter_idx
            )

    def end_session(self):
        self.save_progress()
        logging.info(f"Ending reading session for book {self.book_id}")

    def cleanup(self):
        """Releases WebEngine resources."""
        self.viewer.setHtml("")
        self.viewer.page().profile().clearHttpCache()
        process = psutil.Process(os.getpid())
        logging.info(f"RAM after cleanup: {process.memory_info().rss / 1024 / 1024:.2f} MB")

__all__ = ["ReaderView"]
