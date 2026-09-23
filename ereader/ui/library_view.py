from pathlib import Path
import logging
import collections
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QListView, QTableView, QAbstractItemView, QMenu, QFileDialog,
    QPushButton, QStackedWidget, QLabel, QFrame, QMessageBox,
    QHeaderView, QStyledItemDelegate
)
from PyQt6.QtGui import QIcon, QPixmap, QImage, QPainter, QColor
from PyQt6.QtCore import (
    pyqtSignal, Qt, QSize, QThreadPool, QAbstractListModel,
    QModelIndex, QRunnable, QObject, QSortFilterProxyModel,
    QPersistentModelIndex, QRect
)

from ereader.library import scan_folder, get_file_hash

class LibraryItem:
    def __init__(self, is_folder, name, path, data=None):
        self.is_folder = is_folder
        self.name = name
        self.path = str(path)
        self.data = data # Book dict if not folder

class CoverSignals(QObject):
    cover_loaded = pyqtSignal(QPersistentModelIndex, QPixmap)

class CoverLoader(QRunnable):
    def __init__(self, index, path, is_folder=False, sub_covers=None):
        super().__init__()
        self.index = QPersistentModelIndex(index)
        self.path = path
        self.is_folder = is_folder
        self.sub_covers = sub_covers or []
        self.signals = CoverSignals()

    def run(self):
        if not self.index.isValid():
            return
        try:
            if self.is_folder:
                pixmap = self._generate_folder_cover()
            else:
                image = QImage(self.path)
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image.scaled(150, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    return
            self.signals.cover_loaded.emit(self.index, pixmap)
        except Exception as e:
            logging.error(f"Error loading cover {self.path}: {e}")

    def _generate_folder_cover(self):
        size = QSize(150, 220)
        result = QPixmap(size)
        result.fill(QColor("#2a2a2a"))
        painter = QPainter(result)
        
        w, h = size.width() // 2, size.height() // 2
        rects = [
            QRect(0, 0, w, h),
            QRect(w, 0, w, h),
            QRect(0, h, w, h),
            QRect(w, h, w, h)
        ]
        
        for i, cover_path in enumerate(self.sub_covers[:4]):
            if cover_path and Path(cover_path).exists():
                img = QImage(cover_path)
                if not img.isNull():
                    pixmap = QPixmap.fromImage(img.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                    painter.drawPixmap(rects[i], pixmap)
            else:
                painter.fillRect(rects[i], QColor("#333"))
        
        painter.end()
        return result

class BookModel(QAbstractListModel):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.items = [] # List of LibraryItem
        self.current_path = None # None means "Root" (all imports)
        
        self.cover_cache = collections.OrderedDict()
        self.cache_limit = 200
        self.pending_covers = set()
        
        self.placeholder = QPixmap(150, 220)
        self.placeholder.fill(QColor("#2a2a2a"))

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self.items):
            return None

        item = self.items[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            return item.name
        
        elif role == Qt.ItemDataRole.DecorationRole:
            cache_key = item.path
            if cache_key in self.cover_cache:
                return self.cover_cache[cache_key]
            
            if cache_key not in self.pending_covers:
                self.pending_covers.add(cache_key)
                if item.is_folder:
                    # Find some covers in this folder for the thumbnail
                    sub_covers = self._get_folder_preview_covers(item.path)
                    loader = CoverLoader(index, item.path, is_folder=True, sub_covers=sub_covers)
                else:
                    cover_path = item.data.get('cover_path')
                    if cover_path:
                        loader = CoverLoader(index, cover_path)
                    else:
                        return self.placeholder
                
                loader.signals.cover_loaded.connect(self._on_cover_loaded)
                QThreadPool.globalInstance().start(loader)
            
            return self.placeholder

        elif role == Qt.ItemDataRole.UserRole:
            return item
        
        return None

    def _get_folder_preview_covers(self, folder_path):
        # In a real app, this would be a specialized SQL query
        all_books = self.db.list_books()
        covers = []
        for b in all_books:
            if b['file_path'].startswith(folder_path) and b.get('cover_path'):
                covers.append(b['cover_path'])
                if len(covers) >= 4: break
        return covers

    def _on_cover_loaded(self, index, pixmap):
        if not index.isValid(): return
        item = self.items[index.row()]
        self.pending_covers.discard(item.path)
        self.cover_cache[item.path] = pixmap
        if len(self.cover_cache) > self.cache_limit:
            self.cover_cache.popitem(last=False)
        
        model_index = self.index(index.row(), index.column())
        self.dataChanged.emit(model_index, model_index, [Qt.ItemDataRole.DecorationRole])

    def load_path(self, path):
        """Loads items at the given path."""
        self.beginResetModel()
        self.current_path = path
        self.items = []
        
        all_books = self.db.list_books()
        
        if path is None:
            # Root level: show base directories of all books
            roots = set()
            for b in all_books:
                # We'll treat the parent of the book as the folder
                # Actually, let's find the first common parent or just use the direct parents
                p = Path(b['file_path']).parent
                # In this demo, let's just show top-level directories under "Imports"
                # A better way: find unique first-level directories relative to some common roots
                roots.add(str(p))
            
            # To simplify for the user's request, we'll show unique direct folders
            # But let's build a tree.
            # For now, let's just show folders that are direct children of nothing (roots)
            # or if path is None, show all unique folders that contain books.
            
            # User wants "All > Epub > Cuc Tong"
            # Let's implement a real folder tree based on file_path
            folders = set()
            books_at_root = []
            
            for b in all_books:
                bp = Path(b['file_path'])
                # Find direct children of root? 
                # This is tricky because we don't have a single root.
                # Let's find the most common root or just show all unique directories as folders
                # Wait, if current_path is None, let's show unique top-level directories
                
                # Logic: get relative parts.
                parts = bp.parts
                # For simplicity, let's just show the direct parent as a folder
                folders.add(str(bp.parent))
            
            # If we want the nested view, we need to compare current_path with book paths
            pass 

        # Real hierarchical logic:
        folders = set()
        books = []
        
        for b in all_books:
            bp = Path(b['file_path'])
            if path is None:
                # Show top-level directories (e.g. drive letter or root /)
                # But user wants "Epub", "Cuc Tong". 
                # Let's find the depth 1 folders.
                # In Windows: C:\Books\Epub -> show "C:\"? No.
                # Let's take the first directory after some common root or just the first parts.
                # Better: get the parent of the book. 
                # Let's find unique parents and their hierarchy.
                pass
            
            # Let's assume 'path' is the current directory we are browsing.
            # If path is None, we find the common parent of all books and show its children.
            pass

        # RE-IMPLEMENTING load_path with proper logic
        self.items = []
        all_books = self.db.list_books()
        
        if not all_books:
            self.endResetModel()
            return

        # 1. Determine "Root" if None
        if path is None:
            # Find the shallowest common parent? Or just the parents of all books.
            unique_parents = sorted(list(set(str(Path(b['file_path']).parent) for b in all_books)))
            # For the "All" view, show the top-level unique folders
            # E.g. /home/user/Books/Epub, /home/user/Books/PDF -> show "Epub", "PDF"
            # For now, let's just show unique parents as folders.
            for p in unique_parents:
                self.items.append(LibraryItem(True, Path(p).name, p))
        else:
            # Browsing a specific folder
            curr = Path(path)
            subfolders = set()
            for b in all_books:
                bp = Path(b['file_path'])
                if curr in bp.parents:
                    # It's a descendant
                    if bp.parent == curr:
                        # Direct child book
                        self.items.append(LibraryItem(False, b['title'], b['file_path'], b))
                    else:
                        # Indirect descendant, find the direct subfolder
                        # Path: curr / sub / ... / book
                        relative = bp.relative_to(curr)
                        direct_sub = curr / relative.parts[0]
                        subfolders.add(str(direct_sub))
            
            for sf in sorted(list(subfolders)):
                self.items.append(LibraryItem(True, Path(sf).name, sf))
        
        self.endResetModel()

class BreadcrumbBar(QWidget):
    path_clicked = pyqtSignal(object) # None or str

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        self.layout.addStretch() # Push to left? No, usually breadcrumbs are left-aligned.
        
        # Reset layout to left align
        self.layout.takeAt(0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def set_path(self, path):
        # Clear
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # "All" button
        btn_all = QPushButton("All")
        btn_all.setFlat(True)
        btn_all.setStyleSheet("font-weight: bold; font-size: 14px; color: #888;")
        btn_all.clicked.connect(lambda: self.path_clicked.emit(None))
        self.layout.addWidget(btn_all)
        
        if not path:
            btn_all.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
            self.layout.addStretch()
            return
            
        p = Path(path)
        parts = p.parts
        # We don't want to show full absolute path like C:\ Users ...
        # Let's show the last 3 levels or something.
        # Or relative to the roots we found.
        
        for i, part in enumerate(parts):
            self.layout.addWidget(QLabel(">"))
            curr_path = str(Path(*parts[:i+1]))
            btn = QPushButton(part)
            btn.setFlat(True)
            btn.setStyleSheet("font-size: 14px; color: #888; border: none; background: transparent;")
            if i == len(parts) - 1:
                # The active part should use the theme's fg color
                btn.setStyleSheet("font-weight: bold; font-size: 14px; color: palette(windowText); border: none; background: transparent;")
            
            # Capture curr_path in closure
            btn.clicked.connect(lambda checked, cp=curr_path: self.path_clicked.emit(cp))
            self.layout.addWidget(btn)
        
        self.layout.addStretch()

class LibraryView(QWidget):
    book_opened = pyqtSignal(int, str)

    def __init__(self, config, db, parent=None):
        super().__init__(parent)
        self.config = config
        self.db = db
        
        self.source_model = BookModel(db)
        self.current_path = None
        
        self._setup_ui()
        self.refresh_library()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # Toolbar
        self.toolbar = QFrame()
        toolbar_layout = QHBoxLayout(self.toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.breadcrumb_bar = BreadcrumbBar()
        self.breadcrumb_bar.path_clicked.connect(self._on_breadcrumb_clicked)
        toolbar_layout.addWidget(self.breadcrumb_bar)
        
        toolbar_layout.addStretch()
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search all books...")
        self.search_box.setFixedWidth(200)
        self.search_box.textChanged.connect(self._on_search)
        toolbar_layout.addWidget(self.search_box)
        
        self.btn_import = QPushButton("+")
        self.btn_import.setFixedSize(32, 32)
        self.btn_import.setObjectName("ImportButton")
        self.btn_import.clicked.connect(self._on_import_clicked)
        toolbar_layout.addWidget(self.btn_import)
        
        self.main_layout.addWidget(self.toolbar)

        # Grid View
        self.grid_view = QListView()
        self.grid_view.setViewMode(QListView.ViewMode.IconMode)
        self.grid_view.setIconSize(QSize(150, 220))
        self.grid_view.setGridSize(QSize(180, 280))
        self.grid_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid_view.setMovement(QListView.Movement.Static)
        self.grid_view.setSpacing(10)
        self.grid_view.setWordWrap(True)
        self.grid_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.grid_view.doubleClicked.connect(self._on_item_double_clicked)
        self.grid_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid_view.customContextMenuRequested.connect(self._show_context_menu)
        
        # Style handled via global theme QSS
        self.grid_view.setObjectName("LibraryGrid")
        
        self.main_layout.addWidget(self.grid_view)
        self.grid_view.setModel(self.source_model)

    def refresh_library(self):
        self.source_model.load_path(self.current_path)
        self.breadcrumb_bar.set_path(self.current_path)

    def _on_breadcrumb_clicked(self, path):
        self.current_path = path
        self.refresh_library()

    def _on_reset_progress(self, book_id):
        confirm = QMessageBox.question(self, "Reset Progress", "Are you sure you want to reset reading progress for this book?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            # We'll just delete the progress record
            with self.db.transaction() as cursor:
                cursor.execute("DELETE FROM progress WHERE book_id=?", (book_id,))
            self.refresh_library()

    def _on_item_double_clicked(self, index):
        item = self.source_model.data(index, Qt.ItemDataRole.UserRole)
        if item.is_folder:
            self.current_path = item.path
            self.refresh_library()
        else:
            self.book_opened.emit(item.data['id'], item.data['file_path'])

    def _on_import_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Book Folder")
        if folder:
            from ereader.concurrency import TaskRunner
            self.import_runner = TaskRunner("Importing Books", scan_folder, Path(folder), self.db)
            self.import_runner.finished_task.connect(self.refresh_library)
            self.import_runner.start()

    def _on_search(self, text):
        if not text:
            self.refresh_library()
            return
            
        # Global search: ignore folders, show all matches from DB
        all_books = self.db.list_books()
        self.source_model.beginResetModel()
        self.source_model.items = []
        for b in all_books:
            if text.lower() in b['title'].lower() or text.lower() in (b['author'] or "").lower():
                self.source_model.items.append(LibraryItem(False, b['title'], b['file_path'], b))
        self.source_model.endResetModel()

    def _show_context_menu(self, pos):
        index = self.grid_view.indexAt(pos)
        if not index.isValid(): return
        
        item = self.source_model.data(index, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        if item.is_folder:
            menu.addAction("Open Folder", lambda: self._on_item_double_clicked(index))
        else:
            menu.addAction("Open Book", lambda: self._on_item_double_clicked(index))
            menu.addAction("Book Details")
            menu.addSeparator()
            menu.addAction("Reset Progress", lambda: self._on_reset_progress(item.data['id']))
            menu.addSeparator()
            menu.addAction("Delete from Library")
        
        menu.exec(self.grid_view.mapToGlobal(pos))


# TODO / EXTENSION POINTS:
# 1. Add progress bar overlay on book covers in GridView.
# 2. Implement drag-and-drop for importing books.
# 3. Add collections/tags sidebar.
# 4. Implement advanced sorting and filtering logic.
