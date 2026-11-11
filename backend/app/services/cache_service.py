import json
import logging
import hashlib

from redis.exceptions import RedisError

from app.core.config import settings
from app.database.connections import redis_client


logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "cacherag:answer:"

def build_cache_key(
    collection_id: str,
    collection_version: int,
    question: str,
    web_search_enabled: bool = False,
) -> str:
    """Build a cache key for a question and a specific collection version."""

    normalized_question = " ".join(question.lower().split())

    question_hash = hashlib.sha256(
        normalized_question.encode("utf-8")
    ).hexdigest()

    search_mode = "web:on" if web_search_enabled else "web:off"

    return (
        f"{CACHE_KEY_PREFIX}"
        f"{collection_id}:"
        f"v{collection_version}:"
        f"{search_mode}:"
        f"{question_hash}"
    )



def get_cached_answer_with_status(
    cache_key: str,
) -> tuple[dict | None, bool]:
    """
    Return (cached answer, Redis availability).

    True means Redis was reachable.
    False means Redis encountered a connection/operation error.
    """

    try:
        cached_data = redis_client.get(cache_key)

        if cached_data is None:
            return None, True

        return json.loads(cached_data), True

    except RedisError as error:
        logger.warning("Redis cache read failed: %s", error)
        return None, False

    except json.JSONDecodeError as error:
        logger.warning("Invalid JSON in Redis cache: %s", error)
        return None, True


def get_cached_answer(cache_key: str) -> dict | None:
    """Retrieve a cached answer. Return None on a miss or Redis failure."""

    cached_answer, _ = get_cached_answer_with_status(cache_key)

    return cached_answer



def set_cached_answer(cache_key: str, response: dict) -> bool:
    """Store an answer and its sources in Redis with a TTL."""

    try:
        serialized_response = json.dumps(response)

        redis_client.setex(
            cache_key,
            settings.cache_ttl_seconds,
            serialized_response,
        )

        return True

    except (RedisError, TypeError, ValueError) as error:
        logger.warning("Redis cache write failed: %s", error)
        return False



def clear_answer_cache() -> int:
    """Delete all Redis and Qdrant semantic cache entries."""

    deleted_count = 0
    pattern = f"{CACHE_KEY_PREFIX}*"
    redis_error = None

    try:
        for key in redis_client.scan_iter(match=pattern, count=100):
            deleted_count += redis_client.delete(key)

    except RedisError as error:
        logger.warning("Redis cache clearing failed: %s", error)
        redis_error = error

    # Also clear semantic cache entries from Qdrant.
    try:
        from app.services.semantic_cache_service import clear_semantic_cache

        semantic_deleted = clear_semantic_cache()

        logger.info(
            "Semantic cache cleared | deleted_points=%s",
            semantic_deleted,
        )

    except Exception:
        logger.exception("Semantic cache clearing failed")

    if redis_error is not None:
        raise redis_error

    return deleted_count



def get_cache_ttl(cache_key: str) -> int:
    """Return the remaining TTL for a cache entry."""

    return redis_client.ttl(cache_key)


def invalidate_collection_cache(collection_id: str) -> int:
    """Delete Redis and semantic cache entries for one collection."""

    deleted_count = 0
    pattern = f"{CACHE_KEY_PREFIX}{collection_id}:*"

    try:
        for key in redis_client.scan_iter(match=pattern, count=100):
            deleted_count += redis_client.delete(key)

    except RedisError as error:
        logger.warning(
            "Collection Redis cache invalidation failed for %s: %s",
            collection_id,
            error,
        )

    # Also invalidate semantic entries in Qdrant.
    try:
        from app.services.semantic_cache_service import (
            invalidate_semantic_cache_for_collection,
        )

        semantic_deleted = invalidate_semantic_cache_for_collection(
            collection_id
        )

        logger.info(
            "Collection semantic cache invalidated | "
            "collection_id=%s | success=%s",
            collection_id,
            semantic_deleted,
        )

    except Exception:
        logger.exception(
            "Collection semantic cache invalidation failed: %s",
            collection_id,
        )

    return deleted_count

