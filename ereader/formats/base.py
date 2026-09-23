from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


class UnsupportedFormatError(Exception):
    """Raised when a file format is not supported or parsing fails."""
    pass


@dataclass
class TOCItem:
    """Represents an item in the Table of Contents."""
    title: str
    level: int
    position: str  # Can be a page index or CFI (Canonical Fragment Identifier)


@dataclass
class Page:
    """Represents a single rendered page of the document."""
    index: int
    text: str
    html: Optional[str] = None


class Document(ABC):
    """
    Abstract base class for all document parsers.
    Defines the interface for reading different book formats.
    """

    def __init__(self, path: Path):
        self.path = path
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {path}")

    @property
    @abstractmethod
    def title(self) -> str:
        """Returns the book title."""
        pass

    @property
    @abstractmethod
    def author(self) -> str:
        """Returns the book author."""
        pass

    @property
    @abstractmethod
    def format(self) -> str:
        """Returns the format string (e.g., 'EPUB', 'TXT')."""
        pass

    @property
    @abstractmethod
    def toc(self) -> List[TOCItem]:
        """Returns the table of contents."""
        pass

    @property
    @abstractmethod
    def total_pages(self) -> int:
        """Returns total number of pages/sections."""
        pass

    @abstractmethod
    def get_page(self, index: int) -> Page:
        """Retrieves content for a specific page index."""
        pass

    @abstractmethod
    def get_html(self) -> str:
        """Returns the full HTML content for rendering in a WebEngine."""
        pass

    @abstractmethod
    def search(self, query: str) -> List[Tuple[int, str]]:
        """
        Searches for a string in the document.
        Returns a list of (page_index, context_snippet).
        """
        pass


# TODO / EXTENSION POINTS:
# 1. Add support for metadata extraction like publication date, ISBN, etc.
# 2. Implement 'streamed' parsing for very large documents.
# 3. Add methods for cover image extraction.
# 4. Support for document bookmarks/anchors within the parser level.
