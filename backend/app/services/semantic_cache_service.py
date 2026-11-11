
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


SEMANTIC_CACHE_COLLECTION = "cacherag_semantic_cache"
VECTOR_SIZE = 384


def create_semantic_cache_collection() -> None:
    """Create the semantic cache collection if it does not exist."""

    existing_collections = qdrant_client.get_collections().collections

    collection_exists = any(
        collection.name == SEMANTIC_CACHE_COLLECTION
        for collection in existing_collections
    )

    if not collection_exists:
        qdrant_client.create_collection(
            collection_name=SEMANTIC_CACHE_COLLECTION,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )


def store_semantic_cache_entry(
    question: str,
    embedding: list[float],
    cache_key: str,
    collection_id: str,
    collection_version: int,
    web_search_enabled: bool,
) -> str:
    """Store a question embedding and its Redis answer-cache key."""

    point_id = str(uuid.uuid4())

    point = PointStruct(
        id=point_id,
        vector=embedding,
        payload={
            "question": question,
            "cache_key": cache_key,
            "collection_id": collection_id,
            "collection_version": collection_version,
            "web_search_enabled": web_search_enabled,
        },
    )

    qdrant_client.upsert(
        collection_name=SEMANTIC_CACHE_COLLECTION,
        points=[point],
    )

    return point_id


def search_semantic_cache(
    embedding: list[float],
    collection_id: str,
    collection_version: int,
    web_search_enabled: bool,
    score_threshold: float = 0.90,
    limit: int = 5,
) -> list[dict]:
    """Find semantically similar cached questions."""

    search_results = qdrant_client.query_points(
        collection_name=SEMANTIC_CACHE_COLLECTION,
        query=embedding,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="collection_id",
                    match=MatchValue(value=collection_id),
                ),
                FieldCondition(
                    key="collection_version",
                    match=MatchValue(value=collection_version),
                ),
                FieldCondition(
                    key="web_search_enabled",
                    match=MatchValue(value=web_search_enabled),
                ),
            ]
        ),
        limit=limit,
        with_payload=True,
    ).points

    results = []

    for point in search_results:
        if point.score < score_threshold:
            continue

        results.append(
            {
                "point_id": point.id,
                "question": point.payload["question"],
                "cache_key": point.payload["cache_key"],
                "score": point.score,
            }
        )

    return results


def delete_semantic_cache_point(point_id: str) -> None:
    """Delete one semantic cache entry by its Qdrant point ID."""

    qdrant_client.delete(
        collection_name=SEMANTIC_CACHE_COLLECTION,
        points_selector=[point_id],
    )


def invalidate_semantic_cache_for_collection(
    collection_id: str,
) -> int:
    """Delete semantic cache entries belonging to one collection."""

    result = qdrant_client.delete(
        collection_name=SEMANTIC_CACHE_COLLECTION,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="collection_id",
                    match=MatchValue(value=collection_id),
                )
            ]
        ),
    )

    return result.status == "completed"


def clear_semantic_cache() -> int:
    """Delete all semantic cache entries without deleting the collection."""

    deleted_count = 0
    offset = None

    while True:
        points, next_offset = qdrant_client.scroll(
            collection_name=SEMANTIC_CACHE_COLLECTION,
            limit=100,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )

        if not points:
            break

        point_ids = [point.id for point in points]

        result = qdrant_client.delete(
            collection_name=SEMANTIC_CACHE_COLLECTION,
            points_selector=point_ids,
        )

        if result.status == "completed":
            deleted_count += len(point_ids)

        offset = next_offset

        if offset is None:
            break

    return deleted_count
