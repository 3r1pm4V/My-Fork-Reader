import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


class Database:
    """
    SQLite database manager for the E-Reader.
    Handles schema initialization and core CRUD operations.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Initializes connection and creates schema if needed."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self._create_schema()
            logging.info(f"Connected to database at {self.db_path}")
        except sqlite3.Error as e:
            logging.error(f"Database connection error: {e}")
            raise

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed.")

    @contextmanager
    def transaction(self):
        """Context manager for safe database transactions."""
        if not self.conn:
            self.connect()
        try:
            yield self.conn.cursor()
            self.conn.commit()
        except sqlite3.Error as e:
            self.conn.rollback()
            logging.error(f"Transaction failed: {e}")
            raise

    def _create_schema(self):
        """Creates the initial database tables."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT,
                file_path TEXT UNIQUE NOT NULL,
                format TEXT,
                cover_path TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_read TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS progress (
                book_id INTEGER PRIMARY KEY,
                percentage REAL DEFAULT 0,
                cfi TEXT, -- For EPUB locations
                page_number INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                content TEXT NOT NULL,
                selection_text TEXT,
                cfi TEXT,
                color TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                title TEXT,
                cfi TEXT,
                page_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS collection_books (
                collection_id INTEGER,
                book_id INTEGER,
                PRIMARY KEY (collection_id, book_id),
                FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
            )
            """
        ]
        with self.transaction() as cursor:
            for query in queries:
                cursor.execute(query)

    # --- Book CRUD ---

    def add_book(self, title: str, file_path: str, author: str = None, book_format: str = None) -> int:
        """Adds a new book to the library."""
        query = "INSERT INTO books (title, author, file_path, format) VALUES (?, ?, ?, ?)"
        with self.transaction() as cursor:
            cursor.execute(query, (title, author, file_path, book_format))
            return cursor.lastrowid

    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single book record."""
        query = "SELECT * FROM books WHERE id = ?"
        with self.transaction() as cursor:
            cursor.execute(query, (book_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_books(self) -> List[Dict[str, Any]]:
        """Lists all books in the library."""
        query = "SELECT * FROM books ORDER BY added_at DESC"
        with self.transaction() as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    # --- Progress & Annotations ---

    def update_progress(self, book_id: int, percentage: float, cfi: str = None, page_number: int = None):
        """Updates or inserts reading progress for a book."""
        query = """
            INSERT INTO progress (book_id, percentage, cfi, page_number, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(book_id) DO UPDATE SET
                percentage=excluded.percentage,
                cfi=excluded.cfi,
                page_number=excluded.page_number,
                updated_at=excluded.updated_at
        """
        with self.transaction() as cursor:
            cursor.execute(query, (book_id, percentage, cfi, page_number))
            cursor.execute("UPDATE books SET last_read = CURRENT_TIMESTAMP WHERE id = ?", (book_id,))

    def add_annotation(self, book_id: int, content: str, selection_text: str = None, cfi: str = None) -> int:
        query = "INSERT INTO annotations (book_id, content, selection_text, cfi) VALUES (?, ?, ?, ?)"
        with self.transaction() as cursor:
            cursor.execute(query, (book_id, content, selection_text, cfi))
            return cursor.lastrowid

    def list_annotations(self, book_id: int) -> List[Dict[str, Any]]:
        query = "SELECT * FROM annotations WHERE book_id = ? ORDER BY created_at DESC"
        with self.transaction() as cursor:
            cursor.execute(query, (book_id,))
            return [dict(row) for row in cursor.fetchall()]

    # --- Bookmarks ---

    def add_bookmark(self, book_id: int, title: str, cfi: str = None, page_number: int = None) -> int:
        query = "INSERT INTO bookmarks (book_id, title, cfi, page_number) VALUES (?, ?, ?, ?)"
        with self.transaction() as cursor:
            cursor.execute(query, (book_id, title, cfi, page_number))
            return cursor.lastrowid

    def list_bookmarks(self, book_id: int) -> List[Dict[str, Any]]:
        query = "SELECT * FROM bookmarks WHERE book_id = ? ORDER BY created_at DESC"
        with self.transaction() as cursor:
            cursor.execute(query, (book_id,))
            return [dict(row) for row in cursor.fetchall()]


# TODO / EXTENSION POINTS:
# 1. Add full-text search (FTS5) for book content/annotations.
# 2. Implement database migrations using Alembic (if complexity grows).
# 3. Add support for 'Series' and 'Tags' relationship tables.
# 4. Implement a cleanup job for orphaned file paths.
