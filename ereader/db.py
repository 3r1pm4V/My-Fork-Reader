import sqlite3
import logging
import threading
import time
from pathlib import Path
from contextlib import contextmanager
from ereader.models import Book, Annotation, Progress, Bookmark, ReadingSession

class Database:
    """
    Handles persistence using SQLite.
    Optimized with WAL mode and connection pooling per thread.
    """
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    @property
    def connection(self):
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._setup_connection(self._local.conn)
        return self._local.conn

    def _setup_connection(self, conn):
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")
        conn.execute("PRAGMA foreign_keys=ON")

    @contextmanager
    def transaction(self):
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def _init_db(self):
        with self.transaction() as cursor:
            # Books table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT,
                    file_path TEXT UNIQUE NOT NULL,
                    cover_path TEXT,
                    format TEXT,
                    hash TEXT UNIQUE,
                    added_at INTEGER,
                    last_read_at INTEGER
                )
            """)
            
            # Migration: Ensure all columns exist (for older databases)
            cursor.execute("PRAGMA table_info(books)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            required_columns = {
                'hash': 'TEXT',
                'added_at': 'INTEGER',
                'last_read_at': 'INTEGER',
                'cover_path': 'TEXT',
                'format': 'TEXT'
            }
            
            for col_name, col_type in required_columns.items():
                if col_name not in columns:
                    logging.info(f"Migrating database: Adding '{col_name}' column to 'books' table.")
                    try:
                        cursor.execute(f"ALTER TABLE books ADD COLUMN {col_name} {col_type}")
                        if col_name == 'hash':
                            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_book_hash_unique ON books(hash)")
                    except sqlite3.OperationalError as e:
                        logging.warning(f"Migration warning for {col_name}: {e}")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_hash ON books(hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_last_read ON books(last_read_at)")
            
            # Multi-device progress
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS progress (
                    book_id INTEGER,
                    device_id TEXT,
                    percentage REAL,
                    cfi TEXT,
                    page_number INTEGER,
                    updated_at INTEGER,
                    PRIMARY KEY (book_id, device_id),
                    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                )
            """)
            
            # Migration for progress table
            cursor.execute("PRAGMA table_info(progress)")
            prog_cols = {row[1] for row in cursor.fetchall()}
            if 'device_id' not in prog_cols and prog_cols:
                # Table exists but no device_id. This is a bit complex for a PK change in SQLite.
                # Usually we'd rename, create new, copy, drop.
                # But for 'progress', we can probably just drop it if it's old and broken.
                logging.info("Migrating progress table: Recreating to add device_id.")
                cursor.execute("DROP TABLE progress")
                cursor.execute("""
                    CREATE TABLE progress (
                        book_id INTEGER,
                        device_id TEXT,
                        percentage REAL,
                        cfi TEXT,
                        page_number INTEGER,
                        updated_at INTEGER,
                        PRIMARY KEY (book_id, device_id),
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                    )
                """)

            # Annotations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS annotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER,
                    text TEXT NOT NULL,
                    comment TEXT,
                    cfi TEXT NOT NULL,
                    color TEXT DEFAULT '#ffff00',
                    created_at INTEGER,
                    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                )
            """)

            # Bookmarks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER,
                    title TEXT,
                    cfi TEXT NOT NULL,
                    created_at INTEGER,
                    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                )
            """)

            # Content Cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS book_content_cache (
                    book_hash TEXT NOT NULL,
                    chapter_index INTEGER NOT NULL,
                    html BLOB NOT NULL,
                    cached_at INTEGER NOT NULL,
                    PRIMARY KEY (book_hash, chapter_index)
                )
            """)

    def add_book(self, book: Book) -> int:
        """Adds a book or returns existing ID if file_path already exists. Updates cover if missing."""
        query = """
            INSERT INTO books (title, author, file_path, cover_path, format, hash, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET 
                cover_path = COALESCE(excluded.cover_path, books.cover_path),
                hash = excluded.hash
        """
        with self.transaction() as cursor:
            try:
                cursor.execute(query, (
                    book.title, book.author, book.file_path, 
                    book.cover_path, book.format, book.hash, book.added_at
                ))
                if cursor.lastrowid:
                    return cursor.lastrowid
                
                # If ON CONFLICT happened, get existing id
                cursor.execute("SELECT id FROM books WHERE file_path=?", (book.file_path,))
                return cursor.fetchone()[0]
            except sqlite3.IntegrityError:
                cursor.execute("SELECT id FROM books WHERE file_path=?", (book.file_path,))
                return cursor.fetchone()[0]

    def update_progress(self, book_id: int, percentage: float, cfi: str, page_num: int, device_id: str = "local"):
        query = """
            INSERT INTO progress (book_id, device_id, percentage, cfi, page_number, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(book_id, device_id) DO UPDATE SET
                percentage=excluded.percentage,
                cfi=excluded.cfi,
                page_number=excluded.page_number,
                updated_at=excluded.updated_at
        """
        with self.transaction() as cursor:
            cursor.execute(query, (book_id, device_id, percentage, cfi, page_num, int(time.time())))
            cursor.execute("UPDATE books SET last_read_at=? WHERE id=?", (int(time.time()), book_id))

    def get_latest_progress(self, book_id: int) -> dict | None:
        query = "SELECT * FROM progress WHERE book_id=? ORDER BY updated_at DESC LIMIT 1"
        with self.transaction() as cursor:
            cursor.execute(query, (book_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_book_by_path(self, file_path: str) -> dict | None:
        query = "SELECT * FROM books WHERE file_path=?"
        with self.transaction() as cursor:
            cursor.execute(query, (file_path,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_books(self, limit: int = -1, offset: int = 0) -> list[dict]:
        query = "SELECT * FROM books ORDER BY last_read_at DESC, added_at DESC LIMIT ? OFFSET ?"
        with self.transaction() as cursor:
            cursor.execute(query, (limit, offset))
            return [dict(row) for row in cursor.fetchall()]

    def connect(self):
        """Pre-emptively establishes connection."""
        _ = self.connection

    def clear_all_cache(self):
        """Deletes all entries from book_content_cache."""
        with self.transaction() as cursor:
            cursor.execute("DELETE FROM book_content_cache")

    def cache_size_bytes(self) -> int:
        """Returns the total size of cached HTML content in bytes."""
        with self.transaction() as cursor:
            cursor.execute("SELECT SUM(LENGTH(html)) FROM book_content_cache")
            res = cursor.fetchone()[0]
            return res if res else 0

    def cleanup_oldest_cache(self, target_size_bytes: int):
        """Removes oldest cache entries until total size is below target."""
        current_size = self.cache_size_bytes()
        if current_size <= target_size_bytes:
            return
            
        with self.transaction() as cursor:
            cursor.execute("SELECT book_hash, chapter_index, LENGTH(html) FROM book_content_cache ORDER BY cached_at ASC")
            rows = cursor.fetchall()
            
            to_delete = []
            running_size = current_size
            for row in rows:
                to_delete.append((row[0], row[1]))
                running_size -= row[2]
                if running_size <= target_size_bytes:
                    break
            
            for bh, ci in to_delete:
                cursor.execute("DELETE FROM book_content_cache WHERE book_hash=? AND chapter_index=?", (bh, ci))

    def vacuum(self):
        """Reclaims unused space in the database file."""
        self.connection.execute("VACUUM")

    def list_annotations(self, book_id: int) -> list[dict]:
        query = "SELECT * FROM annotations WHERE book_id=? ORDER BY created_at DESC"
        with self.transaction() as cursor:
            cursor.execute(query, (book_id,))
            return [dict(row) for row in cursor.fetchall()]

    def list_bookmarks(self, book_id: int) -> list[dict]:
        query = "SELECT * FROM bookmarks WHERE book_id=? ORDER BY created_at DESC"
        with self.transaction() as cursor:
            cursor.execute(query, (book_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_cached_chapter(self, book_hash: str, chapter_index: int) -> bytes | None:
        query = "SELECT html FROM book_content_cache WHERE book_hash=? AND chapter_index=?"
        with self.transaction() as cursor:
            cursor.execute(query, (book_hash, chapter_index))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_cached_chapter(self, book_hash: str, chapter_index: int, html_blob: bytes):
        query = """
            INSERT INTO book_content_cache (book_hash, chapter_index, html, cached_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(book_hash, chapter_index) DO UPDATE SET
                html=excluded.html,
                cached_at=excluded.cached_at
        """
        with self.transaction() as cursor:
            cursor.execute(query, (book_hash, chapter_index, html_blob, int(time.time())))

    def close(self):
        if hasattr(self._local, "conn"):
            self._local.conn.execute("PRAGMA optimize")
            self._local.conn.close()
            del self._local.conn

__all__ = ["Database"]
