
import re

from rank_bm25 import BM25Okapi
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
)

from app.database.connections import qdrant_client
from app.services.qdrant_service import COLLECTION_NAME


def tokenize(text: str) -> list[str]:
    """Convert text into lowercase searchable words."""
    return re.findall(r"\b\w+\b", text.lower())


def search_chunks_bm25(
    question: str,
    collection_id: str,
    limit: int = 5,
) -> list[dict]:
    """Find document chunks using BM25 keyword relevance."""

    # 1. Retrieve all chunks belonging to this collection.
    all_points = []
    next_offset = None

    while True:
        points, next_offset = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="collection_id",
                        match=MatchValue(value=collection_id),
                    )
                ]
            ),
            limit=256,
            offset=next_offset,
            with_payload=True,
            with_vectors=False,
        )

        all_points.extend(points)

        if next_offset is None:
            break

    if not all_points:
        return []

    # 2. Extract text from each document chunk.
    documents = [
        point.payload["text"]
        for point in all_points
    ]

    # 3. Tokenize the document chunks.
    tokenized_documents = [
        tokenize(document)
        for document in documents
    ]

    # 4. Build the BM25 keyword-search model.
    bm25 = BM25Okapi(tokenized_documents)

    # 5. Tokenize the user's question.
    tokenized_question = tokenize(question)

    if not tokenized_question:
        return []

    # 6. Calculate BM25 relevance scores.
    scores = bm25.get_scores(tokenized_question)

    # 7. Sort chunks by their BM25 scores.
    ranked_indices = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )

    # 8. Return the highest-ranking chunks.
    results = []

    for index in ranked_indices[:limit]:
        if scores[index] <= 0:
            continue

        payload = all_points[index].payload

        results.append(
            {
                "score": float(scores[index]),
                "document_id": payload["document_id"],
                "filename": payload["filename"],
                "page_number": payload["page_number"],
                "chunk_index": payload["chunk_index"],
                "text": payload["text"],
            }
        )

    return results

