import pytest
from ereader.db import Database

@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "test_library.db"
    database = Database(str(db_file))
    database.connect()
    yield database
    database.close()

def test_book_crud(db):
    book_id = db.add_book("Test Title", "path/to/book.epub", "Test Author", "EPUB")
    assert book_id == 1
    
    book = db.get_book(book_id)
    assert book['title'] == "Test Title"
    assert book['author'] == "Test Author"
    
    books = db.list_books()
    assert len(books) == 1

def test_progress_update(db):
    db.add_book("Title", "path", "Author", "TXT")
    db.update_progress(1, 50.5, "cfi-123", 10)
    
    # We query the progress table directly via transaction for verification
    with db.transaction() as cursor:
        cursor.execute("SELECT * FROM progress WHERE book_id = 1")
        row = cursor.fetchone()
        assert row['percentage'] == 50.5
        assert row['page_number'] == 10

def test_annotations(db):
    db.add_book("Title", "path", "Author", "TXT")
    db.add_annotation(1, "Note content", "Selected text", "pos-1")
    
    annos = db.list_annotations(1)
    assert len(annos) == 1
    assert annos[0]['content'] == "Note content"

def test_bookmarks(db):
    db.add_book("Title", "path", "Author", "TXT")
    db.add_bookmark(1, "B1", "pos-1", 5)
    
    bookmarks = db.list_bookmarks(1)
    assert len(bookmarks) == 1
    assert bookmarks[0]['title'] == "B1"
