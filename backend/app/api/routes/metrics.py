import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.request_metric import RequestMetric


router = APIRouter(
    prefix="/metrics",
    tags=["Monitoring"],
)


@router.get("/summary")
def get_metrics_summary(
    db: Session = Depends(get_db),
):
    """Return aggregated RAG request performance metrics."""

    total_requests = (
        db.query(func.count(RequestMetric.id)).scalar() or 0
    )

    cache_hits = (
        db.query(func.count(RequestMetric.id))
        .filter(RequestMetric.cache_status == "hit")
        .scalar() or 0
    )

    cache_misses = (
        db.query(func.count(RequestMetric.id))
        .filter(RequestMetric.cache_status == "miss")
        .scalar() or 0
    )

    successful_requests = (
        db.query(func.count(RequestMetric.id))
        .filter(RequestMetric.success.is_(True))
        .scalar() or 0
    )

    failed_requests = total_requests - successful_requests

    def average_time(column):
        return round(
            db.query(func.avg(column)).scalar() or 0.0,
            2,
        )

    return {
        "total_requests": total_requests,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "cache_hit_rate_percent": round(
            (cache_hits / total_requests) * 100
            if total_requests else 0.0,
            2,
        ),
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "success_rate_percent": round(
            (successful_requests / total_requests) * 100
            if total_requests else 0.0,
            2,
        ),
        "average_response_time_ms": average_time(
            RequestMetric.response_time_ms
        ),
        "average_cache_lookup_time_ms": average_time(
            RequestMetric.cache_lookup_time_ms
        ),
        "average_retrieval_time_ms": average_time(
            RequestMetric.retrieval_time_ms
        ),
        "average_rerank_time_ms": average_time(
            RequestMetric.rerank_time_ms
        ),
        "average_llm_time_ms": average_time(
            RequestMetric.llm_time_ms
        ),
        "average_cache_write_time_ms": average_time(
            RequestMetric.cache_write_time_ms
        ),
    }


@router.get("/requests")
def get_request_metrics(
    limit: int = Query(default=50, ge=1, le=500),
    collection_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    """Return recent RAG request metrics."""

    query = db.query(RequestMetric)

    if collection_id is not None:
        query = query.filter(
            RequestMetric.collection_id == collection_id
        )

    records = (
        query.order_by(RequestMetric.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "count": len(records),
        "requests": [
            {
                "id": str(record.id),
                "collection_id": (
                    str(record.collection_id)
                    if record.collection_id else None
                ),
                "question": record.question,
                "cache_status": record.cache_status,
                "response_time_ms": record.response_time_ms,
                "cache_lookup_time_ms": record.cache_lookup_time_ms,
                "retrieval_time_ms": record.retrieval_time_ms,
                "rerank_time_ms": record.rerank_time_ms,
                "llm_time_ms": record.llm_time_ms,
                "cache_write_time_ms": record.cache_write_time_ms,
                "success": record.success,
                "created_at": record.created_at.isoformat(),
            }
            for record in records
        ],
    }

@router.get("/comparison")
def compare_cache_performance(
    db: Session = Depends(get_db),
):
    """Compare average response times for cache hits and misses."""

    miss_average = (
        db.query(func.avg(RequestMetric.response_time_ms))
        .filter(RequestMetric.cache_status == "miss")
        .scalar()
    )

    hit_average = (
        db.query(func.avg(RequestMetric.response_time_ms))
        .filter(RequestMetric.cache_status == "hit")
        .scalar()
    )

    miss_average = float(miss_average or 0.0)
    hit_average = float(hit_average or 0.0)

    speedup = (
        miss_average / hit_average
        if hit_average > 0
        else None
    )

    time_saved = (
        miss_average - hit_average
        if miss_average > 0 and hit_average > 0
        else None
    )

    return {
        "uncached_average_ms": round(miss_average, 2),
        "cached_average_ms": round(hit_average, 2),
        "speedup_factor": round(speedup, 2) if speedup else None,
        "time_saved_ms": round(time_saved, 2) if time_saved is not None else None,
    }