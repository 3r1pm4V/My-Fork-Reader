from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt


class SearchDialog(QDialog):
    """
    Dialog for searching text within the current document.
    """
    result_selected = pyqtSignal(object)  # Position of the result

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Search Input
        search_layout = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter text to find...")
        self.input.returnPressed.connect(self._on_search)
        
        self.btn_search = QPushButton("Search")
        self.btn_search.clicked.connect(self._on_search)
        
        search_layout.addWidget(self.input)
        search_layout.addWidget(self.btn_search)
        layout.addLayout(search_layout)

        # Result List
        self.results_label = QLabel("0 results found")
        layout.addWidget(self.results_label)
        
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_selected)
        layout.addWidget(self.list_widget)

    def set_results(self, results: list[tuple[int, str]]):
        """
        Populates the list with search results.
        Expected format: [(page_index, snippet), ...]
        """
        self.list_widget.clear()
        self.results_label.setText(f"{len(results)} results found")
        
        for pos, snippet in results:
            item = QListWidgetItem(f"p. {pos + 1}: {snippet}")
            item.setData(Qt.ItemDataRole.UserRole, pos)
            self.list_widget.addItem(item)

    def _on_search(self):
        query = self.input.text().strip()
        if not query:
            return
        # The actual search is performed by the parent (MainWindow -> Document)
        # This signal triggers the search process.
        if hasattr(self.parent(), "perform_search"):
            self.parent().perform_search(query)

    def _on_item_selected(self, item):
        pos = item.data(Qt.ItemDataRole.UserRole)
        self.result_selected.emit(pos)
