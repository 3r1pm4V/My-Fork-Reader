import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from ereader.formats.base import Document, TOCItem, Page, UnsupportedFormatError


class EpubParser(Document):
    """
    Parser for EPUB files using ebooklib and BeautifulSoup.
    """

    def __init__(self, path: Path):
        super().__init__(path)
        self._book: Optional[epub.EpubBook] = None
        self._chapters: List[Dict] = []
        self._toc: List[TOCItem] = []
        self._load()

    def _load(self):
        try:
            self._book = epub.read_epub(str(self.path))
            
            # Extract Chapters
            for item in self._book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    self._chapters.append({
                        'id': item.get_id(),
                        'content': item.get_content().decode('utf-8'),
                        'file_name': item.get_name()
                    })

            # Extract TOC
            self._build_toc(self._book.toc)
        except Exception as e:
            raise UnsupportedFormatError(f"Failed to parse EPUB: {e}")

    def _build_toc(self, toc_list, level=0):
        for item in toc_list:
            if isinstance(item, tuple):
                section, sub_items = item
                self._toc.append(TOCItem(title=section.title, level=level, position=section.href))
                self._build_toc(sub_items, level + 1)
            elif isinstance(item, epub.Link):
                self._toc.append(TOCItem(title=item.title, level=level, position=item.href))

    @property
    def title(self) -> str:
        title = self._book.get_metadata('DC', 'title')
        return title[0][0] if title else self.path.stem

    @property
    def author(self) -> str:
        author = self._book.get_metadata('DC', 'creator')
        return author[0][0] if author else "Unknown"

    @property
    def format(self) -> str:
        return "EPUB"

    @property
    def toc(self) -> List[TOCItem]:
        return self._toc

    @property
    def total_pages(self) -> int:
        # In EPUB, we treat each document item (chapter) as a "page" or section
        return len(self._chapters)

    def get_page(self, index: int) -> Page:
        if 0 <= index < len(self._chapters):
            html_content = self._chapters[index]['content']
            soup = BeautifulSoup(html_content, 'lxml')
            text = soup.get_text(separator=' ', strip=True)
            return Page(index=index, text=text, html=html_content)
        raise IndexError("Chapter index out of range")

    def get_html(self) -> str:
        """Merges all chapters into one large HTML for seamless scrolling."""
        full_html = ["<html><body>"]
        for chapter in self._chapters:
            soup = BeautifulSoup(chapter['content'], 'lxml')
            body = soup.find('body')
            if body:
                full_html.append(str(body.decode_contents()))
            else:
                full_html.append(chapter['content'])
        full_html.append("</body></html>")
        return "".join(full_html)

    def search(self, query: str) -> List[Tuple[int, str]]:
        results = []
        query = query.lower()
        for i, chapter in enumerate(self._chapters):
            soup = BeautifulSoup(chapter['content'], 'lxml')
            text = soup.get_text()
            if query in text.lower():
                idx = text.lower().find(query)
                snippet = text[max(0, idx-30):idx+70].replace("\n", " ")
                results.append((i, f"...{snippet}..."))
        return results


# TODO / EXTENSION POINTS:
# 1. Handle internal CSS and images (extract and serve via local server or data URIs).
# 2. Implement better pagination by calculating viewport-based page breaks.
# 3. Support for EPUB3 media overlays and interactive elements.
# 4. Font embedding extraction.
