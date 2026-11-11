from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.collection import Collection
from app.schemas.collection import CollectionCreate, CollectionResponse, CollectionRename

from sqlalchemy import func

from app.models.document import Document
from app.schemas.collection import CollectionListResponse
from fastapi import HTTPException
import uuid
from pathlib import Path

from fastapi import UploadFile, File
from app.schemas.document import DocumentResponse

from datetime import datetime, timezone

import pymupdf

from app.services.document_processor import process_document
from app.services.embedding_service import generate_embeddings
from app.services.qdrant_service import (
    store_chunks,
    delete_document_chunks,
)
from app.services.cache_service import invalidate_collection_cache


router = APIRouter(
    prefix="/collections",
    tags=["Collections"],
)


@router.post(
    "/",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_collection(
    collection_data: CollectionCreate,
    db: Session = Depends(get_db),
):
    
    new_collection = Collection(
        name=collection_data.name,
        description=collection_data.description,
    )

    db.add(new_collection)
    db.commit()
    db.refresh(new_collection)

    return new_collection

@router.get(
    "/",
    response_model=list[CollectionListResponse],
)
def list_collections(
    db: Session = Depends(get_db),
):
    collections = (
        db.query(
            Collection,
            func.count(Document.id).label("document_count"),
        )
        .outerjoin(
            Document,
            Collection.id == Document.collection_id,
        )
        .group_by(Collection.id)
        .all()
    )

    return [
        {
            "id": collection.id,
            "name": collection.name,
            "description": collection.description,
            "version": collection.version,
            "created_at": collection.created_at,
            "updated_at": collection.updated_at,
            "document_count": document_count,
        }
        for collection, document_count in collections
    ]

@router.get(
    "/{collection_id}",
    response_model=CollectionResponse,
)
def get_collection(
    collection_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    collection = db.get(Collection, collection_id)

    if collection is None:
        raise HTTPException(
            status_code=404,
            detail="Collection not found",
        )

    return collection

@router.patch(
    "/{collection_id}",
    response_model=CollectionResponse,
)
def rename_collection(
    collection_id: uuid.UUID,
    collection_data: CollectionRename,
    db: Session = Depends(get_db),
):
    collection = db.get(Collection, collection_id)

    if collection is None:
        raise HTTPException(
            status_code=404,
            detail="Collection not found",
        )

    collection.name = collection_data.name

    db.commit()
    db.refresh(collection)

    return collection


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_collection(
    collection_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    # 1. Find the collection.
    collection = db.get(Collection, collection_id)

    if collection is None:
        raise HTTPException(
            status_code=404,
            detail="Collection not found",
        )

    # 2. Retrieve all documents belonging to this collection.
    documents = (
        db.query(Document)
        .filter(Document.collection_id == collection_id)
        .all()
    )

    # 3. Remember the document IDs and physical file paths.
    document_ids = [str(document.id) for document in documents]
    file_paths = [
        Path(document.storage_path)
        for document in documents
    ]

    # 4. Delete all document vectors from Qdrant.
    try:
        for document_id in document_ids:
            delete_document_chunks(document_id)

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete collection vectors from Qdrant.",
        ) from error

    # 5. Delete the collection and its document records.
    db.delete(collection)
    db.commit()

    # 6. Invalidate all cached answers for this collection.
    invalidate_collection_cache(str(collection_id))

    # 7. Delete all physical document files.

    for file_path in file_paths:
        file_path.unlink(missing_ok=True)

    return None



@router.post(
    "/{collection_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    collection_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 1. Check whether the collection exists.
    collection = db.get(Collection, collection_id)

    if collection is None:
        raise HTTPException(
            status_code=404,
            detail="Collection not found",
        )

    # 2. Validate the filename and extension.
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    original_filename = Path(file.filename).name
    file_extension = Path(original_filename).suffix.lower()

    if file_extension not in [".pdf", ".txt"]:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported",
        )

    # 3. Create a unique storage filename.
    stored_filename = f"{uuid.uuid4()}{file_extension}"

    storage_directory = (
        Path(__file__).resolve().parents[3]
        / "storage"
        / "documents"
    )

    storage_directory.mkdir(parents=True, exist_ok=True)

    file_path = storage_directory / stored_filename

    # 4. Save the uploaded file.
    file_size = 0

    try:
        with file_path.open("wb") as stored_file:
            while chunk := await file.read(1024 * 1024):
                stored_file.write(chunk)
                file_size += len(chunk)
    finally:
        await file.close()

    # 5. Create the document record.
    new_document = Document(
        collection_id=collection_id,
        filename=original_filename,
        file_type=file_extension.lstrip("."),
        storage_path=str(file_path),
        status="pending",
        file_size=file_size,
    )

    try:
        db.add(new_document)
        collection.version += 1
        db.commit()
        db.refresh(new_document)

        # Remove cached answers from previous collection versions.
        invalidate_collection_cache(str(collection_id))

    except Exception:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise

    # 6. Start automatic document processing.
    try:
        new_document.status = "processing"
        db.commit()

        chunks = process_document(
            file_path=str(file_path),
            document_id=str(new_document.id),
            filename=original_filename,
        )

        # 7. Calculate the document page count.
        if file_extension == ".pdf":
            with pymupdf.open(str(file_path)) as pdf:
                page_count = len(pdf)
        else:
            page_count = 1 if chunks else 0

        # 8. Generate embeddings for the extracted chunks.
        if chunks:
            texts = [chunk["text"] for chunk in chunks]
            embeddings = generate_embeddings(texts)

            # 9. Store document chunks and embeddings in Qdrant.
            store_chunks(
                chunks=chunks,
                embeddings=embeddings,
                collection_id=str(collection_id),
            )

        # 10. Mark the document as successfully processed.
        new_document.page_count = page_count
        new_document.chunk_count = len(chunks)
        new_document.status = "completed"
        new_document.error_message = None
        new_document.processed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(new_document)

    except Exception as error:
        # 11. Record processing failure.
        db.rollback()

        failed_document = db.get(Document, new_document.id)

        if failed_document is not None:
            failed_document.status = "failed"
            failed_document.error_message = str(error)[:1000]
            failed_document.processed_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(failed_document)

            return failed_document

        raise

    return new_document



@router.get(
    "/{collection_id}/documents",
    response_model=list[DocumentResponse],
)
def list_documents(
    collection_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    # 1. Check whether the collection exists.
    collection = db.get(Collection, collection_id)

    if collection is None:
        raise HTTPException(
            status_code=404,
            detail="Collection not found",
        )

    # 2. Retrieve documents belonging to this collection.
    documents = (
        db.query(Document)
        .filter(Document.collection_id == collection_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )

    return documents
