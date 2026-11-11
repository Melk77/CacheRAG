
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.collection import Collection
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.services.qdrant_service import delete_document_chunks
from app.services.cache_service import invalidate_collection_cache


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return document


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    collection = db.get(Collection, document.collection_id)

    file_path = Path(document.storage_path)
    document_id_str = str(document.id)

    try:
        delete_document_chunks(document_id_str)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete document vectors from Qdrant.",
        ) from error

    if collection is not None:
        collection.version += 1

    db.delete(document)
    db.commit()

    if collection is not None:
        invalidate_collection_cache(str(collection.id))

    file_path.unlink(missing_ok=True)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
