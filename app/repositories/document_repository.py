from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.document import Document

class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, document: Document) -> Document:
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def find_latest_doc_id_by_prefix(self, prefix: str) -> str:
        """
        Find the latest document ID with the given prefix.
        Example: For prefix 'ASIS', it will find the latest ID like 'ASIS-000123'
        """
        query = text("""
            SELECT doc_id 
            FROM TM_DOCUMENTS 
            WHERE doc_id LIKE CONCAT(:prefix, '-%')
            ORDER BY doc_id DESC 
            LIMIT 1
        """)
        
        result = await self.db.execute(query, {"prefix": prefix})
        doc_id=result.scalar()
        return doc_id if doc_id else None

# Create a singleton instance
document_repository = None

def init_document_repository(db: AsyncSession):
    global document_repository
    document_repository = DocumentRepository(db)



