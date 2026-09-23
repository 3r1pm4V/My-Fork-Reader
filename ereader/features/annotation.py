import logging
from ereader.models import Annotation

class AnnotationManager:
    """
    Handles logic for creating, deleting, and searching annotations.
    Actual storage is delegated to the Database class.
    """
    def __init__(self, db):
        self.db = db

    def add_annotation(self, book_id: int, text: str, cfi: str, color: str = "#ffff00", comment: str | None = None) -> int:
        ann = Annotation(
            book_id=book_id,
            text=text,
            cfi=cfi,
            color=color,
            comment=comment
        )
        # Assuming db has add_annotation method
        with self.db.transaction() as cursor:
            query = """
                INSERT INTO annotations (book_id, text, comment, cfi, color, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query, (ann.book_id, ann.text, ann.comment, ann.cfi, ann.color, ann.created_at))
            return cursor.lastrowid

    def list_annotations(self, book_id: int) -> list[Annotation]:
        query = "SELECT * FROM annotations WHERE book_id=? ORDER BY created_at DESC"
        with self.db.transaction() as cursor:
            cursor.execute(query, (book_id,))
            rows = cursor.fetchall()
            return [Annotation(**dict(row)) for row in rows]

    def delete_annotation(self, ann_id: int):
        query = "DELETE FROM annotations WHERE id=?"
        with self.db.transaction() as cursor:
            cursor.execute(query, (ann_id,))

__all__ = ["AnnotationManager"]
