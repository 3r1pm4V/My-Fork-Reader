import chardet
from pathlib import Path
from typing import List, Tuple, Optional
from ereader.formats.base import Document, TOCItem, Page, UnsupportedFormatError


class TxtParser(Document):
    """
    Parser for plain text files.
    Features: Auto-encoding detection, simple character-based paging.
    """

    def __init__(self, path: Path, chars_per_page: int = 2000):
        super().__init__(path)
        self.chars_per_page = chars_per_page
        self._content: str = ""
        self._encoding: str = "utf-8"
        self._pages: List[str] = []
        self._load()

    def _load(self):
        try:
            raw_data = self.path.read_bytes()
            detection = chardet.detect(raw_data)
            self._encoding = detection['encoding'] or 'utf-8'
            self._content = raw_data.decode(self._encoding, errors='replace')
            
            # Simple pagination by character count
            self._pages = [
                self._content[i:i + self.chars_per_page] 
                for i in range(0, len(self._content), self.chars_per_page)
            ]
        except Exception as e:
            raise UnsupportedFormatError(f"Failed to parse TXT: {e}")

    @property
    def title(self) -> str:
        return self.path.stem

    @property
    def author(self) -> str:
        return "Unknown"

    @property
    def format(self) -> str:
        return "TXT"

    @property
    def toc(self) -> List[TOCItem]:
        # TXT files usually don't have a TOC.
        # Extension point: Could detect headers like "Chapter 1"
        return []

    @property
    def total_pages(self) -> int:
        return len(self._pages)

    def get_page(self, index: int) -> Page:
        if 0 <= index < len(self._pages):
            text = self._pages[index]
            # Convert plain text to simple HTML for WebEngine
            html = "".join(f"<p>{line}</p>" for line in text.splitlines() if line.strip())
            return Page(index=index, text=text, html=html)
        raise IndexError("Page index out of range")

    def get_html(self) -> str:
        body = "".join(f"<p>{line}</p>" for line in self._content.splitlines() if line.strip())
        return f"<html><body>{body}</body></html>"

    def search(self, query: str) -> List[Tuple[int, str]]:
        results = []
        query = query.lower()
        for i, page_text in enumerate(self._pages):
            if query in page_text.lower():
                start = max(0, page_text.lower().find(query) - 30)
                snippet = page_text[start:start + 100].replace("\n", " ")
                results.append((i, f"...{snippet}..."))
        return results


# TODO / EXTENSION POINTS:
# 1. Regex-based chapter detection for TOC generation.
# 2. Intelligent paging that doesn't break words or sentences.
# 3. Support for markdown-like formatting detection.
# 4. Handle very large files using memory mapping (mmap).
