import pytest
from pathlib import Path
from ereader.formats.epub_parser import is_valid_epub, EpubParser
from ereader.formats.base import CorruptedBookError

def test_is_valid_epub_with_fake_pdf(tmp_path):
    # Create a fake PDF file with .epub extension
    fake_epub = tmp_path / "fake.epub"
    fake_epub.write_bytes(b"%PDF-1.5\n%EOF")
    
    assert is_valid_epub(fake_epub) is False

def test_is_valid_epub_with_random_data(tmp_path):
    fake_epub = tmp_path / "random.epub"
    fake_epub.write_bytes(b"This is just some text data that is not a zip file.")
    
    assert is_valid_epub(fake_epub) is False

def test_epub_parser_raises_corrupted_error(tmp_path):
    fake_epub = tmp_path / "corrupted.epub"
    fake_epub.write_bytes(b"%PDF-1.5\n%EOF")
    
    with pytest.raises(CorruptedBookError):
        EpubParser(fake_epub)

def test_is_valid_epub_with_minimal_valid_header(tmp_path):
    # A real EPUB starts with PK\x03\x04 and contains application/epub+zip early on
    valid_data = b"PK\x03\x04" + b"A" * 30 + b"mimetypeapplication/epub+zip"
    fake_epub = tmp_path / "valid_header.epub"
    fake_epub.write_bytes(valid_data)
    
    assert is_valid_epub(fake_epub) is True
