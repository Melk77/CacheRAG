
import uuid

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.database.connections import qdrant_client


COLLECTION_NAME = "cacherag_documents"
VECTOR_SIZE = 384


def create_collection() -> None:
    """Create the Qdrant collection if it does not exist."""
    existing_collections = qdrant_client.get_collections().collections

    collection_exists = any(
        collection.name == COLLECTION_NAME
        for collection in existing_collections
    )

    if not collection_exists:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )


def store_chunks(
    chunks: list[dict],
    embeddings: list[list[float]],
    collection_id: str,
) -> None:
    """Store document chunks and their embeddings in Qdrant."""
    if len(chunks) != len(embeddings):
        raise ValueError(
            "The number of chunks must match the number of embeddings"
        )

    if not chunks:
        return

    points = []

    for chunk, embedding in zip(chunks, embeddings):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "collection_id": collection_id,
                    "document_id": chunk["document_id"],
                    "filename": chunk["filename"],
                    "page_number": chunk["page_number"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                },
            )
        )

    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )

    
def search_chunks(
    query_embedding: list[float],
    collection_id: str,
    limit: int = 5,
) -> list[dict]:
    """Find the most relevant document chunks in a collection."""

    search_results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="collection_id",
                    match=MatchValue(value=collection_id),
                )
            ]
        ),
        limit=limit,
        with_payload=True,
    ).points

    results = []

    for point in search_results:
        results.append(
            {
                "score": point.score,
                "document_id": point.payload["document_id"],
                "filename": point.payload["filename"],
                "page_number": point.payload["page_number"],
                "chunk_index": point.payload["chunk_index"],
                "text": point.payload["text"],
            }
        )

    return results

def delete_document_chunks(document_id: str) -> None:
    """Delete all Qdrant chunks belonging to one document."""
    qdrant_client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        ),
    )

