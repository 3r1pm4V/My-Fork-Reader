import logging
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class ProgressDebouncer(QObject):
    """
    Batches progress updates to the database to prevent heavy I/O 
    during rapid page turning or scrolling.
    """
    triggered = pyqtSignal(int, float, str, int)  # book_id, percentage, cfi, page_number

    def __init__(self, db, delay_ms: int = 2000):
        super().__init__()
        self.db = db
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(delay_ms)
        self.timer.timeout.connect(self._flush)
        
        self._pending = None

    def update(self, book_id: int, percentage: float, cfi: str, page_number: int):
        """Queue a progress update."""
        self._pending = (book_id, percentage, cfi, page_number)
        if not self.timer.isActive():
            self.timer.start()

    def flush_now(self):
        """Immediately write pending updates to DB."""
        if self._pending:
            self.timer.stop()
            self._flush()

    def _flush(self):
        if not self._pending:
            return
            
        book_id, percentage, cfi, page_num = self._pending
        self._pending = None
        
        try:
            self.db.update_progress(book_id, percentage, cfi, page_num)
            self.triggered.emit(book_id, percentage, cfi, page_num)
            logging.debug(f"Progress flushed for book {book_id}: {percentage:.2f}%")
        except Exception as e:
            logging.error(f"Failed to flush progress: {e}")

__all__ = ["ProgressDebouncer"]
