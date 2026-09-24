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
            logging.debug(f"MOBI library loaded from: {getattr(mobi, '__file__', 'unknown')}")
        except Exception:
            logging.debug("Could not determine mobi library location", exc_info=True)
        
        self._temp_dir: Path | None = None
        self._html_content: str = ""
        self._load()

    def _load(self) -> None:
        if not hasattr(mobi, "extract"):
            raise UnsupportedFormatError(
                "The installed 'mobi' library is incompatible (missing 'extract'). "
                "Install the correct package with: pip install mobi>=0.3.3"
            )

        try:
            # The 'mobi' package (iscc/mobi, a KindleUnpack fork) exposes
            # mobi.extract(path) -> (tempdir, filepath), NOT mobi.unpack().
            temp_path, extracted_file = mobi.extract(str(self.path))
            self._temp_dir = Path(temp_path)
            extracted_file = Path(extracted_file)

            if extracted_file.suffix.lower() in (".html", ".xhtml", ".htm") and extracted_file.exists():
                self._html_content = extracted_file.read_text(encoding="utf-8", errors="replace")
            else:
                # Some mobi files extract to an .epub; fall back to scanning
                # the temp dir for any HTML content it produced.
                html_files = sorted(self._temp_dir.rglob("*.html")) + sorted(self._temp_dir.rglob("*.xhtml"))
                if html_files:
                    self._html_content = html_files[0].read_text(encoding="utf-8", errors="replace")
                else:
                    raise UnsupportedFormatError("No HTML content found in unpacked MOBI file.")

        except UnsupportedFormatError:
            raise
        except Exception as e:
            raise UnsupportedFormatError(f"Failed to parse MOBI: {e}") from e

    def __del__(self):
        """Cleanup temporary files when object is destroyed."""
        if hasattr(self, '_temp_dir') and self._temp_dir and self._temp_dir.exists():
            import shutil
            try:
                shutil.rmtree(self._temp_dir)
            except Exception:
                logging.debug("Failed to remove MOBI temp dir", exc_info=True)

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
            except Exception:
                logging.debug(f"Could not read MOBI cover candidate for {self.path.name}", exc_info=True)
        return None

    def search(self, query: str) -> list[tuple[int, str]]:
        return []
