from bs4 import BeautifulSoup
from pathlib import Path
from ereader.formats.base import Document, TOCItem, Page, UnsupportedFormatError


class HtmlParser(Document):
    """
    Parser for HTML/HTM files.
    Uses BeautifulSoup with lxml for robust parsing.
    """

    def __init__(self, path: Path):
        super().__init__(path)
        self._soup: BeautifulSoup | None = None
        self._clean_html: str = ""
        self._text: str = ""
        self._load()

    def _load(self):
        try:
            content = self.path.read_text(encoding='utf-8', errors='replace')
            self._soup = BeautifulSoup(content, 'lxml')
            
            # Remove scripts and styles
            for script in self._soup(["script", "style"]):
                script.decompose()
            
            self._text = self._soup.get_text(separator=' ', strip=True)
            self._clean_html = str(self._soup)
        except Exception as e:
            raise UnsupportedFormatError(f"Failed to parse HTML: {e}")

    @property
    def title(self) -> str:
        if self._soup and self._soup.title:
            return self._soup.title.string
        return self.path.stem

    @property
    def author(self) -> str:
        if not self._soup:
            return "Unknown"
        # Try to find meta author
        author_meta = self._soup.find("meta", attrs={"name": "author"})
        if author_meta:
            return author_meta.get("content", "Unknown")
        return "Unknown"

    @property
    def format(self) -> str:
        return "HTML"

    @property
    def toc(self) -> list[TOCItem]:
        if not self._soup:
            return []
        # Generate TOC from H1-H3 tags
        toc = []
        headers = self._soup.find_all(['h1', 'h2', 'h3'])
        for i, h in enumerate(headers):
            level = int(h.name[1]) - 1
            toc.append(TOCItem(title=h.get_text().strip(), level=level, position=f"header-{i}"))
        return toc

    @property
    def total_pages(self) -> int:
        return 1  # HTML is usually one single document

    def get_page(self, index: int) -> Page:
        if index == 0:
            return Page(index=0, text=self._text, html=self._clean_html)
        raise IndexError("HTML only has one page")

    def get_html(self) -> str:
        return self._clean_html

    def search(self, query: str) -> list[tuple[int, str]]:
        results = []
        query = query.lower()
        if query in self._text.lower():
            idx = self._text.lower().find(query)
            snippet = self._text[max(0, idx-30):idx+70]
            results.append((0, f"...{snippet}..."))
        return results
