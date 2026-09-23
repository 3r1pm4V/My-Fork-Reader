from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

class UnsupportedFormatError(Exception):
    """Raised when a file format is not supported or parsing fails."""
    pass

class CorruptedBookError(Exception):
    """Raised when a file is identified as a different format or is corrupted."""
    pass

class ParseError(Exception):
    """Raised when the parser fails to read a valid file."""
    pass

class BookNotFoundError(Exception):
    """Raised when the book file is missing on disk."""
    pass

@dataclass
class TOCItem:
    """Represents an item in the Table of Contents."""
    title: str
    level: int
    position: str

@dataclass
class Page:
    """Represents a single rendered page of the document."""
    index: int
    text: str
    html: str | None = None

class Document(ABC):
    """
    Abstract base class for all document parsers.
    """
    def __init__(self, path: Path):
        self.path = path
        if not self.path.exists():
            raise BookNotFoundError(f"File not found: {path}")

    @property
    @abstractmethod
    def title(self) -> str: pass

    @property
    @abstractmethod
    def author(self) -> str: pass

    @property
    @abstractmethod
    def format(self) -> str: pass

    @property
    @abstractmethod
    def toc(self) -> list[TOCItem]: pass

    @property
    @abstractmethod
    def total_pages(self) -> int: pass

    @abstractmethod
    def get_page(self, index: int) -> Page: pass

    @abstractmethod
    def get_html(self) -> str: pass

    @abstractmethod
    def search(self, query: str) -> list[tuple[int, str]]: pass

    def get_cover(self) -> bytes | None: return None

    def get_metadata_dict(self) -> dict:
        return {
            "title": self.title,
            "author": self.author,
            "format": self.format,
        }
