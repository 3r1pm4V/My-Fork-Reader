import pytest
from pathlib import Path
from ereader.formats.txt_parser import TxtParser

def test_txt_parsing_utf8(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("Hello World\nLine 2", encoding='utf-8')
    
    parser = TxtParser(p, chars_per_page=10)
    assert parser.title == "test"
    assert parser.total_pages > 1
    
    page = parser.get_page(0)
    assert "Hello" in page.text

def test_txt_encoding_detection(tmp_path):
    p = tmp_path / "latin.txt"
    # Create file with Latin-1 specific characters
    content = "Héllò Látìn".encode('latin-1')
    p.write_bytes(content)
    
    parser = TxtParser(p)
    assert "Héllò" in parser.get_page(0).text

def test_txt_search(tmp_path):
    p = tmp_path / "search.txt"
    p.write_text("The quick brown fox jumps over the lazy dog", encoding='utf-8')
    
    parser = TxtParser(p)
    results = parser.search("fox")
    assert len(results) == 1
    assert results[0][0] == 0 # Page 0
    assert "fox" in results[0][1]

def test_txt_html_generation(tmp_path):
    p = tmp_path / "html.txt"
    p.write_text("Line 1\n\nLine 2", encoding='utf-8')
    
    parser = TxtParser(p)
    html = parser.get_html()
    assert "<p>Line 1</p>" in html
    assert "<p>Line 2</p>" in html
