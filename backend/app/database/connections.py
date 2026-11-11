
from redis import Redis
from qdrant_client import QdrantClient
from sqlalchemy import create_engine, text

from app.core.config import settings


# PostgreSQL connection
postgres_engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)


# Redis connection
redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=5,
)


# Qdrant connection
qdrant_client = QdrantClient(
    url=settings.qdrant_url,
    timeout=5,
)


def check_postgres() -> bool:
    with postgres_engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def check_redis() -> bool:
    return redis_client.ping()


def check_qdrant() -> bool:
    qdrant_client.get_collections()
    return True
