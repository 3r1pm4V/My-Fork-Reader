from lxml import etree
from pathlib import Path
from typing import List, Tuple, Optional
from ereader.formats.base import Document, TOCItem, Page, UnsupportedFormatError


class Fb2Parser(Document):
    """
    Parser for FictionBook 2.0 (FB2) files using lxml.
    """

    def __init__(self, path: Path):
        super().__init__(path)
        self._tree: Optional[etree._ElementTree] = None
        self._ns = {'fb': 'http://www.gribuser.ru/xml/fictionbook/2.0'}
        self._load()

    def _load(self):
        try:
            # Note: FB2 can be encoded in various ways, lxml usually handles the XML declaration
            self._tree = etree.parse(str(self.path))
        except Exception as e:
            raise UnsupportedFormatError(f"Failed to parse FB2: {e}")

    def _get_text_content(self, element) -> str:
        return "".join(element.itertext())

    @property
    def title(self) -> str:
        title_node = self._tree.find('.//fb:book-title', namespaces=self._ns)
        return title_node.text if title_node is not None else self.path.stem

    @property
    def author(self) -> str:
        author_node = self._tree.find('.//fb:author', namespaces=self._ns)
        if author_node is not None:
            first = author_node.find('fb:first-name', namespaces=self._ns)
            last = author_node.find('fb:last-name', namespaces=self._ns)
            return f"{first.text if first is not None else ''} {last.text if last is not None else ''}".strip()
        return "Unknown"

    @property
    def format(self) -> str:
        return "FB2"

    @property
    def toc(self) -> List[TOCItem]:
        toc = []
        sections = self._tree.findall('.//fb:section', namespaces=self._ns)
        for i, section in enumerate(sections):
            title_node = section.find('fb:title', namespaces=self._ns)
            if title_node is not None:
                title_text = self._get_text_content(title_node).strip()
                if title_text:
                    toc.append(TOCItem(title=title_text, level=0, position=str(i)))
        return toc

    @property
    def total_pages(self) -> int:
        sections = self._tree.findall('.//fb:section', namespaces=self._ns)
        return len(sections) if sections else 1

    def get_page(self, index: int) -> Page:
        sections = self._tree.findall('.//fb:section', namespaces=self._ns)
        if 0 <= index < len(sections):
            section = sections[index]
            text = self._get_text_content(section)
            # Simple FB2 to HTML conversion
            html = f"<div>{etree.tostring(section, encoding='unicode', method='html')}</div>"
            return Page(index=index, text=text, html=html)
        raise IndexError("Section index out of range")

    def get_html(self) -> str:
        body = self._tree.find('.//fb:body', namespaces=self._ns)
        if body is not None:
            return f"<html><body>{etree.tostring(body, encoding='unicode', method='html')}</body></html>"
        return "<html><body>No content found</body></html>"

    def search(self, query: str) -> List[Tuple[int, str]]:
        results = []
        query = query.lower()
        sections = self._tree.findall('.//fb:section', namespaces=self._ns)
        for i, section in enumerate(sections):
            text = self._get_text_content(section)
            if query in text.lower():
                idx = text.lower().find(query)
                snippet = text[max(0, idx-30):idx+70]
                results.append((i, f"...{snippet}..."))
        return results


# TODO / EXTENSION POINTS:
# 1. Full XSLT transformation for professional rendering.
# 2. Extraction of binary images stored in FB2.
# 3. Support for footnotes and comments as popups.
# 4. Handle nested sections for deeper TOC hierarchy.
