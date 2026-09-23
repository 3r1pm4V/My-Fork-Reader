from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QListWidget,
    QListWidgetItem, QLineEdit, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
import logging

from ereader.formats.base import TOCItem


class Sidebar(QWidget):
    """
    Sidebar containing TOC, Bookmarks, Notes, and Search.
    Inspired by Readest UI.
    """
    navigate_requested = pyqtSignal(object)
    search_requested = pyqtSignal(str)
    pinned_changed = pyqtSignal(bool)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.is_pinned = False
        self._setup_ui()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Sidebar Header
        self.header = QFrame()
        self.header.setObjectName("SidebarHeader")
        self.header.setStyleSheet("border-bottom: 1px solid #333; background: #222;")
        header_layout = QHBoxLayout(self.header)
        
        self.title_label = QLabel("Navigation")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #888;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setFixedWidth(30)
        self.pin_btn.setStyleSheet("border: none; background: transparent;")
        self.pin_btn.clicked.connect(self._toggle_pin)
        header_layout.addWidget(self.pin_btn)
        
        self.layout.addWidget(self.header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        
        # 1. Contents (TOC)
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderHidden(True)
        self.toc_tree.itemClicked.connect(self._on_toc_clicked)
        self.tabs.addTab(self.toc_tree, "Contents")

        # 2. Bookmarks
        self.bookmark_list = QListWidget()
        self.bookmark_list.itemClicked.connect(self._on_bookmark_clicked)
        self.tabs.addTab(self.bookmark_list, "Bookmarks")

        # 3. Notes (Annotations)
        self.anno_list = QListWidget()
        self.anno_list.itemClicked.connect(self._on_anno_clicked)
        self.tabs.addTab(self.anno_list, "Notes")

        # 4. Search
        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search book...")
        self.search_input.returnPressed.connect(self._on_search_requested)
        search_layout.addWidget(self.search_input)
        
        self.search_results = QListWidget()
        self.search_results.itemClicked.connect(self._on_search_result_clicked)
        search_layout.addWidget(self.search_results)
        
        self.tabs.addTab(search_tab, "Search")
        
        self.layout.addWidget(self.tabs)

    def set_book_title(self, title: str):
        self.title_label.setText(title)

    def set_toc(self, toc_items: list[TOCItem]):
        """Populates the TOC tree widget."""
        self.toc_tree.clear()
        for item in toc_items:
            tree_item = QTreeWidgetItem([item.title])
            tree_item.setData(0, 100, item.position)
            self.toc_tree.addTopLevelItem(tree_item)

    def load_annotations(self, book_id: int):
        """Loads annotations for the specific book from DB."""
        self.anno_list.clear()
        annos = self.db.list_annotations(book_id)
        for a in annos:
            text = a['text']
            item = QListWidgetItem(f"{text[:30]}...")
            item.setData(100, a['cfi'])
            self.anno_list.addItem(item)

    def load_bookmarks(self, book_id: int):
        """Loads bookmarks from DB."""
        self.bookmark_list.clear()
        bookmarks = self.db.list_bookmarks(book_id)
        for b in bookmarks:
            title = b['title'] or f"Page {b['cfi']}"
            item = QListWidgetItem(title)
            item.setData(100, b['cfi'])
            self.bookmark_list.addItem(item)

    def set_search_results(self, results: list[tuple[int, str]]):
        """Updates the search results list."""
        self.search_results.clear()
        for page_idx, snippet in results:
            item = QListWidgetItem(f"p.{page_idx+1}: {snippet}")
            item.setData(100, page_idx)
            self.search_results.addItem(item)

    def _toggle_pin(self, checked):
        self.is_pinned = checked
        self.pinned_changed.emit(checked)

    def _on_toc_clicked(self, item, column):
        pos = item.data(0, 100)
        if pos is not None:
            self.navigate_requested.emit(pos)

    def _on_anno_clicked(self, item):
        pos = item.data(100)
        if pos is not None:
            self.navigate_requested.emit(pos)

    def _on_bookmark_clicked(self, item):
        pos = item.data(100)
        if pos is not None:
            self.navigate_requested.emit(pos)

    def _on_search_requested(self):
        query = self.search_input.text()
        if query:
            self.search_requested.emit(query)

    def _on_search_result_clicked(self, item):
        pos = item.data(100)
        if pos is not None:
            self.navigate_requested.emit(pos)

# TODO / EXTENSION POINTS:
# 1. Support hierarchical TOC (nested QTreeWidgetItem).
# 2. Add 'Add Bookmark' button and 'Delete' context menu to Sidebar.
# 3. Implement real-time search filtering in TOC/Notes.
# 4. Style items with icons and better preview snippets.
