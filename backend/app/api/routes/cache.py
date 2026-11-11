from fastapi import APIRouter, HTTPException
from redis.exceptions import RedisError

from app.services.cache_service import clear_answer_cache
from app.services.redis_monitoring_service import get_redis_cache_stats


router = APIRouter(
    prefix="/cache",
    tags=["Cache"],
)


@router.delete("/answers")
def clear_cached_answers():
    """Manually clear all CacheRAG answer-cache entries."""

    try:
        deleted_entries = clear_answer_cache()

        return {
            "message": "Answer cache cleared successfully.",
            "deleted_entries": deleted_entries,
        }

    except RedisError:
        raise HTTPException(
            status_code=503,
            detail="Unable to clear the answer cache because Redis is unavailable.",
        )


@router.get("/stats")
def get_cache_statistics():
    """Return Redis memory, cache, and server statistics."""

    try:
        return get_redis_cache_stats()

    except (RedisError, RuntimeError):
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve cache statistics because Redis is unavailable.",
        )