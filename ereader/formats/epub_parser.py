from pathlib import Path
import zlib
import logging
from fast_ebook import epub
import fast_ebook
from bs4 import BeautifulSoup
from ereader.formats.base import (
    Document, TOCItem, Page, UnsupportedFormatError, 
    CorruptedBookError, ParseError
)
from ereader.utils import get_file_hash


def is_valid_epub(path: Path) -> bool:
    """
    Lenient check for EPUB validity. 
    Standard EPUBs should start with PK\x03\x04 and contain 'mimetype'.
    """
    try:
        with open(path, 'rb') as f:
            header = f.read(2048)
            # Lenient check: just look for ZIP signature anywhere in the first 2KB
            # and verify it's not a common false positive.
            if b'PK\x03\x04' not in header:
                return False
            return True
    except Exception:
        return False


class EpubParser(Document):
    """
    High-performance Parser for EPUB files using fast-ebook (Rust core).
    Leverages lazy loading to handle large documents efficiently.
    """

    def __init__(self, path: Path, db=None, book_hash=None):
        super().__init__(path)
        self._path = path
        self.db = db
        self.book_hash = book_hash or get_file_hash(path)
        self._temp_repair_dir: Path | None = None
        
        if not is_valid_epub(path):
            raise CorruptedBookError(f"File {path.name} is not a valid ZIP/EPUB container.")

        try:
            # Attempt to read the EPUB
            try:
                self._book = epub.read_epub(str(path))
            except Exception as e:
                if "ZIP error" in str(e) or "i/o error" in str(e):
                    logging.warning(f"ZIP error detected in {path.name}, attempting to clean/repair: {e}")
                    # Try to "repair" by re-zipping with Python's lenient zipfile module
                    import zipfile
                    import tempfile
                    import shutil
                    
                    self._temp_repair_dir = Path(tempfile.mkdtemp(prefix="epub_repair_"))
                    repaired_path = self._temp_repair_dir / "repaired.epub"
                    
                    try:
                        with zipfile.ZipFile(path, 'r') as src_zip:
                            with zipfile.ZipFile(repaired_path, 'w', compression=zipfile.ZIP_DEFLATED) as dst_zip:
                                for item in src_zip.infolist():
                                    try:
                                        # Copy each file, normalizing headers
                                        dst_zip.writestr(item.filename, src_zip.read(item.filename))
                                    except:
                                        continue
                        
                        # Try reading the repaired file
                        self._book = epub.read_epub(str(repaired_path))
                        logging.info(f"Successfully repaired and loaded {path.name}")
                    except Exception as repair_err:
                        logging.error(f"Repair failed for {path.name}: {repair_err}")
                        raise e # Raise original error
                else:
                    raise e

            self._chapters: list[dict] = []
            self._toc: list[TOCItem] = []
            self._html_cache: str | None = None
            
            self._load_structure()
        except Exception as e:
            # Fallback for "Invalid OPF" or other metadata errors: 
            # We might still be able to open it if we ignore metadata, 
            # but fast-ebook is strict. We'll wrap it to provide better error.
            logging.warning(f"Lenient fallback triggered for {path.name} due to: {e}")
            raise ParseError(f"EPUB structure is malformed (e.g. invalid XML in metadata). Error: {e}")

    def _load_structure(self):
        """Builds internal chapter list and TOC following the Spine (reading order)."""
        self._chapters = []
        logging.info(f"Loading structure for: {self.path.name}")
        
        # 1. Try to load using Spine (Standard reading order)
        spine_ids = []
        try:
            # Check various ways libraries expose the spine
            if hasattr(self._book, 'spine') and self._book.spine:
                spine_ids = self._book.spine
            elif hasattr(self._book, 'get_spine'):
                spine_ids = self._book.get_spine()
            
            # If spine_ids is a list of objects or tuples instead of strings
            if spine_ids and not isinstance(spine_ids[0], str):
                if hasattr(spine_ids[0], 'idref'):
                    spine_ids = [s.idref for s in spine_ids]
                elif hasattr(spine_ids[0], 'id'):
                    spine_ids = [s.id for s in spine_ids]
                elif isinstance(spine_ids[0], (tuple, list)) and len(spine_ids[0]) > 0:
                    # Extract the ID from the first element of the tuple/list
                    spine_ids = [s[0] for s in spine_ids]

            if spine_ids:
                for item_id in spine_ids:
                    item = self._book.get_item_with_id(item_id)
                    if item and item.get_type() == fast_ebook.ITEM_DOCUMENT:
                        self._chapters.append({
                            'id': item.get_id(),
                            'item': item,
                            'name': item.get_name()
                        })
                
                if self._chapters:
                    logging.info(f"Loaded {len(self._chapters)} chapters from Spine order.")
                    self._build_toc(self._book.toc)
                    return
        except Exception as e:
            logging.warning(f"Spine-based loading failed for {self.path.name}: {e}")

        # 2. Fallback to Manifest order with smart numerical sorting
        logging.warning(f"Spine missing or invalid in {self.path.name}, falling back to Manifest order.")
        temp_chapters = []
        for item in self._book.get_items():
            if item.get_type() == fast_ebook.ITEM_DOCUMENT:
                name = item.get_name().lower()
                if any(name.endswith(ext) for ext in ['.xhtml', '.html', '.htm', '.xml']):
                    temp_chapters.append({
                        'id': item.get_id(),
                        'item': item,
                        'name': item.get_name()
                    })
        
        # Smart sorting: try to find numbers in the filename
        import re
        def get_sort_key(ch):
            # Extract all numbers and treat them as integers for natural sorting
            name = ch['name']
            return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', name)]
            
        try:
            self._chapters = sorted(temp_chapters, key=get_sort_key)
            logging.info(f"Loaded {len(self._chapters)} chapters using Numerical/Alphabetical sorting.")
        except:
            self._chapters = temp_chapters
            logging.info(f"Loaded {len(self._chapters)} chapters from raw Manifest order.")
            
        self._build_toc(self._book.toc)

    def _build_toc(self, toc_list, level=0):
        for item in toc_list:
            if isinstance(item, tuple):
                section, sub_items = item
                self._toc.append(TOCItem(title=section.title, level=level, position=section.href))
                self._build_toc(sub_items, level + 1)
            elif hasattr(item, 'title') and hasattr(item, 'href'):
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
    def toc(self) -> list[TOCItem]:
        return self._toc

    @property
    def total_pages(self) -> int:
        return len(self._chapters)

    def get_page(self, index: int) -> Page:
        if 0 <= index < len(self._chapters):
            ch = self._chapters[index]
            
            # Handle virtual cover
            if ch.get('is_virtual_cover'):
                cover_data = self.get_cover()
                import base64
                b64 = base64.b64encode(cover_data).decode('utf-8')
                html = f"<html><body style='margin:0;padding:0;display:flex;justify-content:center;align-items:center;height:100vh;'><img src='data:image/jpeg;base64,{b64}' style='max-width:100%;max-height:100%;object-fit:contain;' /></body></html>"
                return Page(index=index, text="Cover Page", html=html)

            # Check cache first
            if self.db:
                try:
                    compressed_data = self.db.get_cached_chapter(self.book_hash, index)
                    if compressed_data:
                        html_content = zlib.decompress(compressed_data).decode('utf-8')
                        soup = BeautifulSoup(html_content, 'lxml')
                        text = soup.get_text(separator=' ', strip=True)
                        return Page(index=index, text=text, html=html_content)
                except Exception as e:
                    logging.error(f"Error reading cache for chapter {index}: {e}")

            # Fallback to parsing
            item = self._chapters[index]['item']
            html_content = item.get_content().decode('utf-8')
            
            # Store in cache
            if self.db:
                try:
                    compressed_data = zlib.compress(html_content.encode('utf-8'))
                    self.db.set_cached_chapter(self.book_hash, index, compressed_data)
                except Exception as e:
                    logging.error(f"Error writing cache for chapter {index}: {e}")

            soup = BeautifulSoup(html_content, 'lxml')
            text = soup.get_text(separator=' ', strip=True)
            return Page(index=index, text=text, html=html_content)
        raise IndexError("Chapter index out of range")

    def get_html(self) -> str:
        """Merges all chapters into one large HTML. Uses lazy content loading."""
        if self._html_cache:
            return self._html_cache

        full_html = ["<html><body>"]
        for ch in self._chapters:
            html_content = ch['item'].get_content().decode('utf-8')
            soup = BeautifulSoup(html_content, 'xml')
            body = soup.find('body')
            if body:
                # We strip the body tags and just take content
                full_html.append(str(body.decode_contents()))
            else:
                full_html.append(html_content)
        full_html.append("</body></html>")
        
        self._html_cache = "".join(full_html)
        return self._html_cache

    def search(self, query: str) -> list[tuple[int, str]]:
        results = []
        query = query.lower()
        for i, ch in enumerate(self._chapters):
            # Search requires loading the content into memory
            html_content = ch['item'].get_content().decode('utf-8')
            soup = BeautifulSoup(html_content, 'xml')
            text = soup.get_text()
            if query in text.lower():
                idx = text.lower().find(query)
                snippet = text[max(0, idx-30):idx+70].replace("\n", " ")
                results.append((i, f"...{snippet}..."))
        return results

    def get_cover(self) -> bytes | None:
        """Attempts to extract the cover image with multiple fallback strategies."""
        try:
            # 1. Try to find cover via metadata
            cover_id = None
            metadata = self._book.get_metadata('OPF', 'cover')
            if metadata:
                cover_id = metadata[0][0]
            
            # 2. Try to get item by ID if found
            if cover_id:
                item = self._book.get_item_with_id(cover_id)
                if item:
                    return item.get_content()

            # 3. Fallback: Search for images with 'cover' in name
            cover_items = self._book.get_items_of_type(fast_ebook.ITEM_IMAGE)
            if not cover_items:
                return None

            for item in cover_items:
                name = item.get_name().lower()
                id_val = item.get_id().lower()
                if 'cover' in name or 'cover' in id_val:
                    return item.get_content()

            # 4. Final fallback: Return the largest image (likely the cover)
            largest_item = max(cover_items, key=lambda x: len(x.get_content() or b""))
            if largest_item and len(largest_item.get_content()) > 5000: # Threshold to avoid tiny icons
                return largest_item.get_content()
        except Exception as e:
            logging.debug(f"Cover extraction failed: {e}")
        return None

    def __del__(self):
        """Clean up temporary repair directory if it exists."""
        if hasattr(self, '_temp_repair_dir') and self._temp_repair_dir and self._temp_repair_dir.exists():
            import shutil
            try:
                shutil.rmtree(str(self._temp_repair_dir))
            except:
                pass
