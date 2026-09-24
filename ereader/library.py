import logging
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from ereader.utils import get_file_hash, partial_md5
from ereader.formats import get_parser, HAS_FAST_EBOOK
from ereader.models import Book

from ereader.config import get_app_dir

def _ensure_cover(book_hash: str, parser, db) -> str | None:
    """Extracts and saves the book cover if it doesn't already exist."""
    covers_dir = get_app_dir() / "covers"
    covers_dir.mkdir(exist_ok=True)
    
    cover_path = covers_dir / f"{book_hash}.jpg"
    if cover_path.exists():
        return str(cover_path)
        
    try:
        cover_data = parser.get_cover()
        if cover_data:
            cover_path.write_bytes(cover_data)
            return str(cover_path)
    except Exception as e:
        logging.warning(f"Could not extract cover for {parser.path.name}: {e}")
    
    return None

import zipfile
from bs4 import BeautifulSoup

def _try_get_metadata_lenient(path: Path) -> dict:
    """Fallback to manual ZIP parsing if high-level parsers fail."""
    meta = {"title": path.stem, "author": "Unknown", "format": path.suffix[1:].upper()}
    if path.suffix.lower() != ".epub":
        return meta
        
    try:
        with zipfile.ZipFile(path) as z:
            # 1. Find the .opf file path from container.xml
            try:
                container_data = z.read("META-INF/container.xml")
                soup_c = BeautifulSoup(container_data, "lxml-xml")
                rootfile = soup_c.find("rootfile")
                if rootfile and rootfile.get("full-path"):
                    opf_path = rootfile["full-path"]
                    # 2. Parse the OPF file for title/author
                    opf_data = z.read(opf_path)
                    soup_o = BeautifulSoup(opf_data, "lxml-xml")
                    
                    title_tag = soup_o.find("dc:title")
                    if title_tag: meta["title"] = title_tag.get_text(strip=True)
                    
                    creator_tag = soup_o.find("dc:creator")
                    if creator_tag: meta["author"] = creator_tag.get_text(strip=True)
            except Exception:
                logging.debug(f"Lenient EPUB metadata parse (container/opf) failed for {path.name}", exc_info=True)
    except Exception:
        logging.debug(f"Lenient EPUB metadata parse failed for {path.name}", exc_info=True)
    return meta

def scan_folder(folder_path: Path, db, recursive: bool = True) -> tuple[int, int]:
    """
    Scans a folder for books and adds them to the database.
    Handles re-extracting missing covers for existing books.
    """
    patterns = ["*.epub", "*.mobi", "*.azw", "*.azw3", "*.fb2", "*.txt", "*.html"]
    files = []
    for pattern in patterns:
        if recursive:
            files.extend(folder_path.rglob(pattern))
        else:
            files.extend(folder_path.glob(pattern))

    added = 0
    skipped = 0
    
    # Process all files
    for p in files:
        try:
            # Use KOReader-compatible MD5(Binary method) for sync ID
            book_hash = partial_md5(p)
            existing_book = db.get_book_by_path(str(p))
            
            # Check if cover needs refresh
            needs_cover = False
            if existing_book:
                cover_path_str = existing_book.get('cover_path')
                if not cover_path_str or not Path(cover_path_str).exists():
                    needs_cover = True
                else:
                    added += 1 # Already in DB, but we count it as "processed"
                    continue # Skip if everything is fine
            else:
                needs_cover = True

            # If we need cover or it's a new book, we need a parser
            try:
                parser = get_parser(p, db=db)
                title = parser.title or p.stem
                author = parser.author
                fmt = parser.format
                
                cover_path = None
                if needs_cover:
                    cover_path = _ensure_cover(book_hash, parser, db)
            except Exception as e:
                logging.warning(f"Standard parser failed for {p.name}, trying lenient fallback. Error: {e}")
                lenient_meta = _try_get_metadata_lenient(p)
                title = lenient_meta["title"]
                author = lenient_meta["author"]
                fmt = lenient_meta["format"]
                cover_path = None # Won't attempt cover extraction for broken files
            
            book = Book(
                title=title,
                author=author,
                file_path=str(p),
                format=fmt,
                hash=book_hash,
                cover_path=cover_path
            )
            db.add_book(book)
            added += 1
            
        except Exception as e:
            logging.error(f"Failed to process {p.name}: {e}")
            skipped += 1

    logging.info(f"Scan complete: {added} processed/added, {skipped} skipped.")
    return added, skipped

__all__ = ["scan_folder", "get_file_hash"]
