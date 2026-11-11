import logging

from redis.exceptions import RedisError

from app.database.connections import redis_client
from app.services.cache_service import CACHE_KEY_PREFIX


logger = logging.getLogger(__name__)


def get_redis_cache_stats() -> dict:
    """
    Collect Redis server statistics and CacheRAG answer-cache statistics.
    """

    try:
        # 1. Read Redis memory information.
        memory_info = redis_client.info(section="memory")

        # 2. Read Redis command and eviction statistics.
        stats_info = redis_client.info(section="stats")

        # 3. Read Redis server information.
        server_info = redis_client.info(section="server")

        # 4. Count only CacheRAG answer-cache keys.
        cache_key_count = sum(
            1
            for _ in redis_client.scan_iter(
                match=f"{CACHE_KEY_PREFIX}*",
                count=100,
            )
        )

        # 5. Get cache hit and miss counters.
        cache_hits = stats_info.get("keyspace_hits", 0)
        cache_misses = stats_info.get("keyspace_misses", 0)

        total_cache_requests = cache_hits + cache_misses

        hit_rate = (
            (cache_hits / total_cache_requests) * 100
            if total_cache_requests > 0
            else 0.0
        )

        return {
            "status": "connected",
            "cache": {
                "key_prefix": CACHE_KEY_PREFIX,
                "cached_answers": cache_key_count,
                "hits": cache_hits,
                "misses": cache_misses,
                "hit_rate_percent": round(hit_rate, 2),
            },
            "memory": {
                "used_memory_bytes": memory_info.get(
                    "used_memory", 0
                ),
                "used_memory_human": memory_info.get(
                    "used_memory_human", "unknown"
                ),
                "max_memory_bytes": memory_info.get(
                    "maxmemory", 0
                ),
                "max_memory_human": memory_info.get(
                    "maxmemory_human", "unknown"
                ),
                "eviction_policy": memory_info.get(
                    "maxmemory_policy", "unknown"
                ),
            },
            "server": {
                "uptime_seconds": server_info.get(
                    "uptime_in_seconds", 0
                ),
                "connected_clients": redis_client.info(
                    section="clients"
                ).get("connected_clients", 0),
                "total_commands_processed": stats_info.get(
                    "total_commands_processed", 0
                ),
                "evicted_keys": stats_info.get(
                    "evicted_keys", 0
                ),
            },
        }

    except RedisError as error:
        logger.exception("Failed to collect Redis monitoring statistics")
        raise RuntimeError(
            "Unable to collect Redis monitoring statistics."
        ) from error