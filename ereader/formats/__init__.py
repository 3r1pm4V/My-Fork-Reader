import logging
from pathlib import Path
from ereader.formats.base import (
    Document, UnsupportedFormatError, CorruptedBookError, ParseError, BookNotFoundError
)
from ereader.formats.txt_parser import TxtParser
from ereader.formats.html_parser import HtmlParser
from ereader.formats.fb2_parser import Fb2Parser
from ereader.formats.mobi_parser import MobiParser

HAS_FAST_EBOOK = False
try:
    from ereader.formats.epub_parser import EpubParser
    HAS_FAST_EBOOK = True
except ImportError:
    logging.warning("fast-ebook not found. EPUB support disabled.")

PARSERS: dict[str, type[Document]] = {
    '.txt': TxtParser,
    '.html': HtmlParser,
    '.htm': HtmlParser,
    '.fb2': Fb2Parser,
    '.mobi': MobiParser,
    '.azw': MobiParser,
    '.azw3': MobiParser,
}

if HAS_FAST_EBOOK:
    PARSERS['.epub'] = EpubParser

def get_parser(path: Path, db=None) -> Document:
    """
    Factory function to get the appropriate parser for a given file.
    """
    if not path.exists():
        raise BookNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    parser_class = PARSERS.get(ext)
    
    if not parser_class:
        raise UnsupportedFormatError(f"Extension '{ext}' is not supported.")
    
    try:
        if ext == '.epub' and HAS_FAST_EBOOK:
            return parser_class(path, db=db)
        return parser_class(path)
    except (UnsupportedFormatError, CorruptedBookError, ParseError, BookNotFoundError):
        raise
    except Exception as e:
        raise UnsupportedFormatError(f"Error initializing parser for {path.name}: {e}")

__all__ = [
    "get_parser", "Document", "UnsupportedFormatError", 
    "CorruptedBookError", "ParseError", "BookNotFoundError",
    "HAS_FAST_EBOOK"
]
