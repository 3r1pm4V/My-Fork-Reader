import logging
import psutil
import os
import json
from pathlib import Path
from string import Template

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QFrame, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QUrl, QObject, pyqtSlot, QEvent
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PyQt6.QtWebChannel import QWebChannel

from ereader.formats.base import Document
from ereader.ui.themes import theme_manager


class ReaderBridge(QObject):
    """
    Bridge duy nhất cho giao tiếp JS -> Python qua QWebChannel.
    Được đăng ký là 'pybridge' trên window.
    """
    relocated = pyqtSignal(float, str, int, int)  # fraction, cfi, current_page, total_pages
    navRequested = pyqtSignal(str)                 # 'prev' | 'next'
    bridgeReady = pyqtSignal()
    bookReady = pyqtSignal()                       # foliate finished open() + init()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_channel = None

    def set_active_channel(self, channel: QWebChannel | None):
        """Lưu tham chiếu đến QWebChannel hiện tại."""
        self._active_channel = channel

    def cleanup(self, page=None):
        """
        Dọn dẹp và hủy hoàn toàn QWebChannel instance hiện tại:
        - Deregister đối tượng khỏi channel
        - Gỡ channel khỏi page của QWebEngineView
        - Xóa và giải phóng tài nguyên của QWebChannel
        Ngăn chặn rò rỉ bộ nhớ và tích tụ event listener khi re-initialize view.
        """
        if page:
            try:
                page.setWebChannel(None)
            except Exception as e:
                logging.debug(f"[ReaderBridge] Failed to detach web channel from page: {e}")

        if self._active_channel is not None:
            try:
                self._active_channel.deregisterObject(self)
            except Exception as e:
                logging.debug(f"[ReaderBridge] Failed to deregister from channel: {e}")
            try:
                self._active_channel.deleteLater()
            except Exception as e:
                logging.debug(f"[ReaderBridge] Failed to delete channel: {e}")
            self._active_channel = None

        logging.info("[ReaderBridge] Cleanup completed for existing QWebChannel instance.")

    @pyqtSlot(str)
    def onRelocate(self, detail_json: str):
        try:
            data = json.loads(detail_json)
            fraction = float(data.get('fraction', 0.0))
            cfi = str(data.get('cfi', ''))
            
            # Extract page / section info if provided
            current_page = int(data.get('page', 0))
            total_pages = int(data.get('totalPages', 0))
            
            self.relocated.emit(fraction, cfi, current_page, total_pages)
        except Exception as e:
            logging.error(f"[ReaderBridge] Error parsing relocate event: {e}")

    @pyqtSlot(str)
    def onNavRequest(self, direction: str):
        self.navRequested.emit(direction)

    @pyqtSlot()
    def onReady(self):
        logging.info("[ReaderBridge] JS bridge established and ready.")
        self.bridgeReady.emit()

    @pyqtSlot()
    def onBookReady(self):
        logging.info("[ReaderBridge] Book opened and positioned.")
        self.bookReady.emit()


class ReaderView(QWidget):
    back_requested = pyqtSignal()
    page_changed = pyqtSignal(int, int)  # current, total
    book_ready = pyqtSignal()            # book opened + initial position restored

    def __init__(self, config, db, parent=None):
        super().__init__(parent)
        self.config = config
        self.db = db
        self.document: Document | None = None
        self.book_id: int | None = None

        # State tracking derived exclusively from foliate-js
        self._current_fraction = 0.0
        self._current_cfi = ""
        self._current_page = 0
        self._total_pages = 0
        self._is_ready = False

        # Khởi tạo bridge và đăng ký các slot duy nhất
        self._bridge = ReaderBridge()
        self._bridge.relocated.connect(self._on_bridge_relocated)
        self._bridge.navRequested.connect(self._on_bridge_nav_requested)
        self._bridge.bookReady.connect(self._on_bridge_book_ready)

        self._setup_ui()
        self.viewer.page().installEventFilter(self)

    def get_progress_data(self) -> dict:
        """Lấy tiến độ thực tế do foliate-js báo cáo."""
        return {
            "fraction": self._current_fraction,
            "cfi": self._current_cfi
        }

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header bar
        self.header = QFrame()
        self.header.setObjectName("ReaderHeader")
        self.header.setFixedHeight(50)
        h_layout = QHBoxLayout(self.header)
        self.btn_back = QPushButton("←")
        self.btn_back.clicked.connect(self.back_requested)
        h_layout.addWidget(self.btn_back)
        self.title_label = QLabel("Loading...")
        h_layout.addWidget(self.title_label, 1)
        self.main_layout.addWidget(self.header)

        # Container & WebEngineView
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)

        profile = QWebEngineProfile("ereader-profile", self)
        self.viewer = QWebEngineView(profile)

        # Quản lý vòng đời QWebChannel tập trung qua _bridge
        self.channel = None

        settings = self.viewer.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

        self.container_layout.addWidget(self.viewer)
        self.main_layout.addWidget(self.container)

        # Footer bar
        self.footer = QFrame()
        self.footer.setObjectName("ReaderFooter")
        self.footer.setFixedHeight(50)
        f_layout = QHBoxLayout(self.footer)

        self.btn_prev = QPushButton("«")
        self.btn_prev.clicked.connect(self.prev_page)
        f_layout.addWidget(self.btn_prev)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        f_layout.addWidget(self.progress_bar)

        self.page_label = QLabel("Loading...")
        f_layout.addWidget(self.page_label)

        self.btn_next = QPushButton("»")
        self.btn_next.clicked.connect(self.next_page)
        f_layout.addWidget(self.btn_next)

        self.main_layout.addWidget(self.footer)

    def set_document(self, doc: Document, book_id: int):
        """Khởi tạo tài liệu và cấu trúc trang web foliate-js."""
        self.document = doc
        self.book_id = book_id
        self.title_label.setText(doc.title)

        # 1. Dọn dẹp và chuẩn bị Channel trước khi load HTML
        self._bridge.cleanup(page=self.viewer.page())
        self.channel = QWebChannel(self.viewer.page())
        self.channel.registerObject("pybridge", self._bridge)
        self._bridge.set_active_channel(self.channel)
        self.viewer.page().setWebChannel(self.channel)

        # 2. Xử lý đường dẫn
        assets_dir = Path(__file__).parent.parent / "assets" / "foliate-js"
        assets_url = Path(assets_dir).as_uri()
        book_url = Path(doc.path).as_uri()
        
        last_progress = self.db.get_latest_progress(book_id) if self.db else None
        last_cfi = last_progress.get('cfi', None) if last_progress else None
        last_loc_js = json.dumps(last_cfi) if last_cfi else "null"

        # ReaderView is reused between books: reset the state, otherwise
        # get_progress_data() would still return the PREVIOUS book's position
        # until the first relocate event arrives. Seed with the saved local
        # position instead (0 for a book that was never opened).
        self._is_ready = False
        self._current_fraction = float(last_progress.get('percentage') or 0.0) if last_progress else 0.0
        self._current_cfi = last_cfi or ""
        self._current_page = 0
        self._total_pages = 0

        # 3. Tạo template HTML
        # Sử dụng string.Template với cú pháp $variable để tránh xung đột với { } của JavaScript.
        html_template = Template("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        html, body { margin: 0; padding: 0; width: 100vw; height: 100vh; overflow: hidden; }
        #reader-view { width: 100%; height: 100%; display: block; }
    </style>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head>
<body>
    <div id="debug-log" style="color:red; font-size:12px; position:absolute; top:0; left:0; z-index:1000; background: rgba(255,255,255,0.8);"></div>
    <foliate-view id="reader-view"></foliate-view>
    <script type="module">
        import { View } from '$assets_url/view.js';

        // --- Reader theme -------------------------------------------------
        // The book lives inside foliate's own iframe, so the Qt stylesheet
        // never reaches it: colours must be injected through renderer.setStyles().
        // (No JS template literals here: string.Template would treat "dollar{" as a placeholder.)
        window.__theme = $theme_js;
        function buildThemeCss(t) {
            return 'html { background-color: ' + t.bg + ' !important; color: ' + t.fg + ' !important; }\\n'
                 + 'body { background-color: transparent !important; color: ' + t.fg + ' !important; }\\n'
                 + 'body *:not(a):not(img):not(svg):not(image) { color: inherit !important; background-color: transparent !important; }\\n'
                 + 'a:link, a:visited { color: ' + t.accent + ' !important; }\\n';
        }
        window.applyReaderTheme = function(t) {
            window.__theme = t;
            document.documentElement.style.background = t.bg;
            document.body.style.background = t.bg;
            const v = document.getElementById('reader-view');
            if (v && v.renderer && typeof v.renderer.setStyles === 'function') {
                v.renderer.setStyles(buildThemeCss(t));
            }
        };
        
        function log(msg) { console.log(msg); document.getElementById('debug-log').innerHTML += msg + '<br>'; }
        window.onerror = function(msg, url, line) { log('Error: ' + msg + ' at ' + line); };
        
        new QWebChannel(qt.webChannelTransport, function(channel) {
            log('Channel connected');
            window.pybridge = channel.objects.pybridge;
            window.pybridge.onReady();
            const view = document.getElementById('reader-view');
            
            view.addEventListener('relocate', (e) => {
                const d = e.detail || {};
                window.pybridge.onRelocate(JSON.stringify({ 
                    fraction: d.fraction || 0, 
                    cfi: d.cfi || '',
                    page: d.pageItem?.index || 0,
                    totalPages: d.pageItem?.total || 0
                }));
            });
            
            view.open('$book_url')
                .then(function() { 
                    log('Book opened');
                    window.applyReaderTheme(window.__theme);
                    return view.init({ lastLocation: $last_loc_js, showTextStart: true }); 
                })
                .then(function() { log('Initialized'); window.pybridge.onBookReady(); })
                .catch(function(err) { log('Err: ' + err.message); });
        });
    </script>
</body>
</html>""")
        
        theme = self._theme_payload()
        # Avoid a white flash behind the page while foliate is still loading
        self.viewer.page().setBackgroundColor(QColor(theme["bg"]))

        html_content = html_template.safe_substitute(
            assets_url=assets_url,
            book_url=book_url,
            last_loc_js=last_loc_js,
            theme_js=json.dumps(theme)
        )
        
        # Sử dụng baseUrl là thư mục chứa assets để import có thể giải quyết đường dẫn tương đối
        self.viewer.setHtml(html_content, QUrl(assets_url + "/"))

    @pyqtSlot(float, str, int, int)
    def _on_bridge_relocated(self, fraction: float, cfi: str, current_page: int, total_pages: int):
        """Xử lý sự kiện định vị trang duy nhất được gửi từ foliate-js."""
        self._current_fraction = fraction
        self._current_cfi = cfi
        self._current_page = current_page
        self._total_pages = total_pages

        self._update_progress_ui(fraction, cfi)

        # Lưu lại tiến độ vào Database
        if self.book_id and self.db:
            try:
                self.db.update_progress(self.book_id, fraction, cfi=cfi, page_num=current_page)
            except Exception as e:
                logging.error(f"[ReaderView] Failed to save progress to DB: {e}")

        # Relocate events fired while foliate is still opening/restoring the last
        # position must not reach the sync layer (they would overwrite the
        # remote progress with a stale position).
        if not self._is_ready:
            return

        # Phát tín hiệu đồng bộ cho MainWindow
        total_rep = total_pages if total_pages > 0 else (self.document.total_pages if self.document else 1)
        curr_rep = current_page if current_page > 0 else int(fraction * total_rep) + 1
        self.page_changed.emit(curr_rep, total_rep)

    def _on_bridge_book_ready(self):
        self._is_ready = True
        self.book_ready.emit()

    def _update_progress_ui(self, fraction: float, cfi: str):
        pct = max(0, min(100, int(fraction * 100)))
        self.progress_bar.setValue(pct)
        self.page_label.setText(f"{pct}%")

    def _on_bridge_nav_requested(self, direction: str):
        if direction == 'next':
            self.next_page()
        elif direction == 'prev':
            self.prev_page()

    def next_page(self):
        js = """
        (() => {
            const view = document.getElementById('reader-view');
            if (view && typeof view.next === 'function') {
                view.next();
            }
        })();
        """
        self.viewer.page().runJavaScript(js)

    def prev_page(self):
        js = """
        (() => {
            const view = document.getElementById('reader-view');
            if (view && typeof view.prev === 'function') {
                view.prev();
            }
        })();
        """
        self.viewer.page().runJavaScript(js)

    def go_to_percentage(self, percentage: float):
        """Chuyển đến phần trăm tài liệu thông qua foliate-js API."""
        # State is updated by the 'relocate' event once the jump really happened.
        # Sử dụng .replace để tránh xung đột với {} trong JS
        js = """
        (() => {
            const view = document.getElementById('reader-view');
            if (view && typeof view.goToFraction === 'function') {
                Promise.resolve(view.goToFraction(__PERCENTAGE__))
                    .catch(e => console.error('goToFraction failed', e));
            }
        })();
        """.replace('__PERCENTAGE__', str(percentage))
        self.viewer.page().runJavaScript(js)

    def go_to_cfi(self, cfi: str):
        """Chuyển đến CFI cụ thể thông qua foliate-js API."""
        escaped_cfi = json.dumps(cfi)
        # Sử dụng .replace để tránh xung đột với {} trong JS
        js = """
        (() => {
            const view = document.getElementById('reader-view');
            if (view && typeof view.goTo === 'function') {
                view.goTo(__CFI__);
            }
        })();
        """.replace('__CFI__', escaped_cfi)
        self.viewer.page().runJavaScript(js)

    def _theme_payload(self) -> dict:
        v = theme_manager.get_theme_variables(self.config.reading.theme)
        return {"bg": v["bg"], "fg": v["fg"], "accent": v["accent"]}

    def update_display(self):
        """Được MainWindow gọi khi đổi theme hoặc settings: áp theme vào nội dung sách."""
        theme = self._theme_payload()
        page = self.viewer.page()
        page.setBackgroundColor(QColor(theme["bg"]))
        page.runJavaScript(
            "window.applyReaderTheme && window.applyReaderTheme(__THEME__);"
            .replace("__THEME__", json.dumps(theme))
        )

    def save_progress(self):
        """Lưu lại tiến độ hiện tại."""
        if self.book_id and self.db:
            try:
                self.db.update_progress(
                    self.book_id,
                    self._current_fraction,
                    cfi=self._current_cfi,
                    page_num=self._current_page
                )
            except Exception as e:
                logging.error(f"[ReaderView] Error in save_progress: {e}")

    def end_session(self):
        self.save_progress()
        logging.info(f"Ending reading session for book {self.book_id}")

    def cleanup(self):
        """Giải phóng tài nguyên WebEngine và WebChannel khi đóng sách."""
        self._bridge.cleanup(page=self.viewer.page())
        self.channel = None
        self.viewer.setHtml("")
        self.viewer.page().profile().clearHttpCache()
        process = psutil.Process(os.getpid())
        logging.info(f"RAM after cleanup: {process.memory_info().rss / 1024 / 1024:.2f} MB")

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Left:
                self.prev_page()
                return True
            elif event.key() == Qt.Key.Key_Right:
                self.next_page()
                return True
        return super().eventFilter(source, event)


__all__ = ["ReaderView"]
