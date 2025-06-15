from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.document import Document

class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, document: Document) -> Document:
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def find_latest_doc_id_by_prefix(self, prefix: str) -> str:
        """
        Find the latest document ID with the given prefix.
        Example: For prefix 'ASIS', it will find the latest ID like 'ASIS-000123'
        """
        query = text("""
            SELECT doc_id 
            FROM TM_DOCUMENTS 
            WHERE doc_id LIKE :prefix || '-%' 
            ORDER BY doc_id DESC 
            LIMIT 1
        """)
        
        result = self.db.execute(query, {"prefix": prefix}).scalar()
        return result if result else None

# Create a singleton instance
document_repository = None

def init_document_repository(db: Session):
    global document_repository
    document_repository = DocumentRepository(db)


