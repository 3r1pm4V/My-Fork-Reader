from pathlib import Path
from typing import Type, Dict
from ereader.formats.base import Document, UnsupportedFormatError
from ereader.formats.txt_parser import TxtParser
from ereader.formats.epub_parser import EpubParser
from ereader.formats.html_parser import HtmlParser
from ereader.formats.fb2_parser import Fb2Parser
from ereader.formats.mobi_parser import MobiParser

PARSERS: Dict[str, Type[Document]] = {
    '.txt': TxtParser,
    '.epub': EpubParser,
    '.html': HtmlParser,
    '.htm': HtmlParser,
    '.fb2': Fb2Parser,
    '.mobi': MobiParser,
    '.azw': MobiParser,
    '.azw3': MobiParser,
}


def get_parser(path: Path) -> Document:
    """
    Factory function to get the appropriate parser for a given file.
    
    Args:
        path: Path to the book file.
        
    Returns:
        Document: An instance of a Document parser.
        
    Raises:
        UnsupportedFormatError: If the extension is not supported or parsing fails.
    """
    ext = path.suffix.lower()
    parser_class = PARSERS.get(ext)
    
    if not parser_class:
        raise UnsupportedFormatError(f"Extension '{ext}' is not supported.")
    
    try:
        return parser_class(path)
    except Exception as e:
        # Re-raise as UnsupportedFormatError if it's not already
        if not isinstance(e, UnsupportedFormatError):
            raise UnsupportedFormatError(f"Error initializing parser for {path.name}: {e}")
        raise

# TODO / EXTENSION POINTS:
# 1. Add support for PDF (using PyMuPDF or pdfminer).
# 2. Plugin system to allow users to add custom parsers via entry points.
# 3. Support for compressed files (.zip, .rar containing books).
