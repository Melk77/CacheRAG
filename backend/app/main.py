
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

from app.core.config import settings
from app.database.connections import (
    check_postgres,
    check_redis,
    check_qdrant,
)
from app.services.semantic_cache_service import (
    create_semantic_cache_collection,
)
from app.api.routes.collections import router as collections_router
from app.api.routes.documents import router as documents_router
from app.api.routes.chat import router as chat_router
from app.api.routes.cache import router as cache_router
from app.api.routes.metrics import router as metrics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Initializing Qdrant semantic cache collection...")
    create_semantic_cache_collection()
    logging.info("Semantic cache collection is ready.")

    yield


app = FastAPI(
    title=settings.app_name,
    description="Redis-powered Retrieval-Augmented Generation knowledge assistant.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(collections_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(cache_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Welcome to CacheRAG API",
        "status": "running",
    }


@app.get("/health")
def health():
    checks = {
        "postgresql": check_postgres,
        "redis": check_redis,
        "qdrant": check_qdrant,
    }

    services = {}

    for name, check in checks.items():
        try:
            check()
            services[name] = "connected"
        except Exception:
            services[name] = "disconnected"

    all_healthy = all(
        status == "connected" for status in services.values()
    )

    result = {
        "status": "healthy" if all_healthy else "degraded",
        "services": services,
    }

    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content=result,
    )
