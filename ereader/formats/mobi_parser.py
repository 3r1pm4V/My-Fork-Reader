import logging
from pathlib import Path
from ereader.formats.base import Document, TOCItem, Page, UnsupportedFormatError

try:
    import mobi
except ImportError:
    mobi = None


class MobiParser(Document):
    """
    Parser for MOBI/AZW files.
    Depends on the 'mobi' library.
    """

    def __init__(self, path: Path):
        super().__init__(path)
        if mobi is None:
            raise UnsupportedFormatError("The 'mobi' library is not installed. Cannot parse MOBI files.")
        
        try:
            import os
            logging.debug(f"MOBI library loaded from: {getattr(mobi, '__file__', 'unknown')}")
        except:
            pass
        
        self._temp_dir: Path | None = None
        self._html_content: str = ""
        self._load()

    def _load(self):
        try:
            if not hasattr(mobi, 'unpack'):
                # Try fallback if available or raise specific error
                raise UnsupportedFormatError(
                    "The installed 'mobi' library is incompatible (missing 'unpack'). "
                    "Ensure you have the correct 'mobi' package installed."
                )

            # mobi.unpack returns a path to the unpacked HTML
            temp_path, _ = mobi.unpack(str(self.path))
            self._temp_dir = Path(temp_path)
            
            # Find the actual content file (usually .html or .xhtml)
            html_files = list(self._temp_dir.glob("*.html")) + list(self._temp_dir.glob("*.xhtml"))
            if html_files:
                self._html_content = html_files[0].read_text(encoding='utf-8', errors='replace')
            else:
                raise UnsupportedFormatError("No HTML content found in unpacked MOBI file.")
                
        except Exception as e:
            raise UnsupportedFormatError(f"Failed to parse MOBI: {e}")

    def __del__(self):
        """Cleanup temporary files when object is destroyed."""
        if hasattr(self, '_temp_dir') and self._temp_dir and self._temp_dir.exists():
            import shutil
            try:
                shutil.rmtree(self._temp_dir)
            except:
                pass

    @property
    def title(self) -> str:
        return self.path.stem

    @property
    def author(self) -> str:
        return "Unknown"

    @property
    def format(self) -> str:
        return "MOBI"

    @property
    def toc(self) -> list[TOCItem]:
        return []

    @property
    def total_pages(self) -> int:
        return 1

    def get_page(self, index: int) -> Page:
        if index == 0:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(self._html_content, 'lxml')
            text = soup.get_text(separator=' ', strip=True)
            return Page(index=0, text=text, html=self._html_content)
        raise IndexError("MOBI parser currently supports single-page view only")

    def get_html(self) -> str:
        return self._html_content

    def get_cover(self) -> bytes | None:
        """Attempts to find a cover image in the unpacked MOBI content."""
        if not self._temp_dir:
            return None
            
        images_dir = self._temp_dir / "images"
        if not images_dir.exists():
            images_dir = self._temp_dir
            
        # Common cover names or just the first image
        possible_covers = list(images_dir.glob("*cover*.*")) + list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
        if possible_covers:
            try:
                return possible_covers[0].read_bytes()
            except:
                pass
        return None

    def search(self, query: str) -> list[tuple[int, str]]:
        return []
