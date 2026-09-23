from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

@dataclass
class Book:
    id: int | None = None
    title: str = ""
    author: str | None = None
    file_path: str = ""
    cover_path: str | None = None
    format: str = ""
    hash: str = ""
    added_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    last_read_at: int | None = None

@dataclass
class Annotation:
    id: int | None = None
    book_id: int = 0
    text: str = ""
    comment: str | None = None
    cfi: str = ""
    color: str = "#ffff00"
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))

@dataclass
class Progress:
    book_id: int
    device_id: str
    percentage: float
    cfi: str | None = None
    page_number: int | None = None
    updated_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))

@dataclass
class Bookmark:
    id: int | None = None
    book_id: int = 0
    title: str = ""
    cfi: str = ""
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp()))

@dataclass
class ReadingSession:
    id: int | None = None
    book_id: int = 0
    start_time: int = field(default_factory=lambda: int(datetime.now().timestamp()))
    end_time: int | None = None
    pages_read: int = 0

__all__ = ["Book", "Annotation", "Progress", "Bookmark", "ReadingSession"]
