
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.collection import Collection
from app.models.request_metric import RequestMetric
from app.schemas.chat import AskRequest, AskResponse
from app.services.rag_service import answer_question


router = APIRouter(
    prefix="/collections",
    tags=["Chat"],
)


@router.post(
    "/{collection_id}/ask",
    response_model=AskResponse,
)
def ask_question(
    collection_id: uuid.UUID,
    request: AskRequest,
    db: Session = Depends(get_db),
):
    # 1. Check whether the collection exists.
    collection = db.get(Collection, collection_id)

    if collection is None:
        raise HTTPException(
            status_code=404,
            detail="Collection not found",
        )

    # 2. Prepare a container for performance measurements.
    metrics = {}

    # 3. Generate an answer using the RAG pipeline.
    try:
        result = answer_question(
            question=request.question,
            collection_id=str(collection_id),
            collection_version=collection.version,
            web_search_enabled=request.web_search_enabled,
            performance_metrics=metrics,
        )

    except Exception as error:
        logging.exception("RAG answer generation failed")

        raise HTTPException(
            status_code=500,
            detail="Failed to generate an answer.",
        ) from error

    # 4. Save performance measurements in PostgreSQL.
    try:
        metric = RequestMetric(
            collection_id=collection_id,
            question=request.question,
            cache_status=metrics["cache_status"],
            response_time_ms=metrics["response_time_ms"],
            cache_lookup_time_ms=metrics["cache_lookup_time_ms"],
            retrieval_time_ms=metrics["retrieval_time_ms"],
            rerank_time_ms=metrics["rerank_time_ms"],
            llm_time_ms=metrics["llm_time_ms"],
            cache_write_time_ms=metrics["cache_write_time_ms"],
            success=True,
        )

        db.add(metric)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Answer generated, but performance metrics could not be saved.",
        )

    # 5. Return the answer and its sources.
    return result
