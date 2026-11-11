
import logging
import time

from app.services.cache_service import (
    build_cache_key,
    get_cached_answer,
    get_cached_answer_with_status,
    set_cached_answer,
)
from app.services.embedding_service import generate_embedding
from app.services.semantic_cache_service import (
    search_semantic_cache,
    store_semantic_cache_entry,
    delete_semantic_cache_point,
)
from app.services.hybrid_search_service import search_chunks_hybrid
from app.services.reranker_service import rerank_chunks
from app.services.groq_service import (
    generate_answer,
    generate_web_answer,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

INSUFFICIENT_CONTEXT = (
    "I could not find enough information in the selected documents "
    "to answer this question."
)

RERANK_SCORE_THRESHOLD = 0.0
RERANK_LIMIT = 5
SEMANTIC_CACHE_SCORE_THRESHOLD = 0.6


def is_greeting(question: str) -> bool:
    normalized = question.lower().strip(" \t\n.!?,")

    greetings = {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "howdy",
        "hi there",
        "hello there",
    }

    return normalized in greetings


def save_semantic_cache_entry(
    question: str,
    embedding: list[float] | None,
    cache_key: str,
    collection_id: str,
    collection_version: int,
    web_search_enabled: bool,
) -> None:
    """Save a semantic cache entry without interrupting RAG on failure."""

    if embedding is None:
        return

    try:
        store_semantic_cache_entry(
            question=question,
            embedding=embedding,
            cache_key=cache_key,
            collection_id=collection_id,
            collection_version=collection_version,
            web_search_enabled=web_search_enabled,
        )

    except Exception:
        logger.exception("Semantic cache write failed")


def answer_question(
    question: str,
    collection_id: str,
    collection_version: int = 1,
    performance_metrics: dict | None = None,
    web_search_enabled: bool = False,
) -> dict:

    metrics = (
        performance_metrics
        if performance_metrics is not None
        else {}
    )

    metrics.update({
        "cache_status": "miss",
        "response_time_ms": 0.0,
        "cache_lookup_time_ms": 0.0,
        "semantic_cache_lookup_time_ms": 0.0,
        "embedding_time_ms": 0.0,
        "retrieval_time_ms": 0.0,
        "rerank_time_ms": 0.0,
        "llm_time_ms": 0.0,
        "cache_write_time_ms": 0.0,
        "web_search_time_ms": 0.0,
    })

    request_start = time.perf_counter()

    # 1. Handle greetings without running the RAG pipeline.
    if is_greeting(question):
        answer = (
            "Hello! 👋 I'm CacheRAG. Ask me anything about your "
            "selected documents, and I'll help you find the answer."
        )

        total_ms = (
            time.perf_counter() - request_start
        ) * 1000

        metrics["response_time_ms"] = total_ms

        logger.info(
            "RAG performance | result=greeting | total_ms=%.2f",
            total_ms,
        )

        return {
            "answer": answer,
            "sources": [],
        }

    # 2. Build an exact cache key.
    cache_key = build_cache_key(
        collection_id=collection_id,
        collection_version=collection_version,
        question=question,
        web_search_enabled=web_search_enabled,
    )

    # 3. Check exact Redis cache first.
    cache_start = time.perf_counter()

    cached_response = get_cached_answer(cache_key)

    cache_lookup_ms = (
        time.perf_counter() - cache_start
    ) * 1000

    metrics["cache_lookup_time_ms"] = cache_lookup_ms

    if cached_response is not None:
        total_ms = (
            time.perf_counter() - request_start
        ) * 1000

        metrics["cache_status"] = "hit"
        metrics["response_time_ms"] = total_ms

        logger.info(
            "RAG performance | result=exact_cache_hit | "
            "cache_lookup_ms=%.2f | total_ms=%.2f",
            cache_lookup_ms,
            total_ms,
        )

        return cached_response

    # 4. Generate an embedding for semantic cache lookup.
    embedding = None

    embedding_start = time.perf_counter()

    try:
        embedding = generate_embedding(question)

    except Exception:
        logger.exception(
            "Question embedding generation failed; "
            "continuing with normal RAG"
        )

    embedding_ms = (
        time.perf_counter() - embedding_start
    ) * 1000

    metrics["embedding_time_ms"] = embedding_ms

    # 5. Search for a semantically similar cached question.
    if embedding is not None:
        semantic_start = time.perf_counter()

        try:
            semantic_results = search_semantic_cache(
                embedding=embedding,
                collection_id=collection_id,
                collection_version=collection_version,
                web_search_enabled=web_search_enabled,
                score_threshold=SEMANTIC_CACHE_SCORE_THRESHOLD,
                limit=5,
            )

            # Check Redis before returning any semantic match.
            # A Qdrant entry alone does not guarantee that its
            # corresponding Redis answer has not expired.
            for result in semantic_results:
                semantic_response, redis_available = (
                    get_cached_answer_with_status(result["cache_key"])
                )

                if semantic_response is not None:
                    semantic_lookup_ms = (
                        time.perf_counter() - semantic_start
                    ) * 1000

                    metrics["semantic_cache_lookup_time_ms"] = (
                        semantic_lookup_ms
                    )

                    total_ms = (
                        time.perf_counter() - request_start
                    ) * 1000

                    metrics["cache_status"] = "semantic_hit"
                    metrics["response_time_ms"] = total_ms

                    logger.info(
                        "RAG performance | result=semantic_cache_hit | "
                        "similarity=%.4f | embedding_ms=%.2f | "
                        "semantic_lookup_ms=%.2f | total_ms=%.2f",
                        result["score"],
                        embedding_ms,
                        semantic_lookup_ms,
                        total_ms,
                    )

                    return semantic_response

                # Redis is unavailable. Do not assume the answer expired.
                # Preserve the Qdrant semantic-cache entry.
                if not redis_available:
                    logger.warning(
                        "Skipping semantic cache cleanup because Redis "
                        "is unavailable."
                    )
                    break

                # Redis is reachable, but the answer is missing or invalid.
                # Remove the stale Qdrant reference.
                try:
                    delete_semantic_cache_point(result["point_id"])

                except Exception:
                    logger.exception(
                        "Failed to delete stale semantic cache entry"
                    )

        except Exception:
            logger.exception(
                "Semantic cache lookup failed; "
                "continuing with normal RAG"
            )

        semantic_lookup_ms = (
            time.perf_counter() - semantic_start
        ) * 1000

        metrics["semantic_cache_lookup_time_ms"] = (
            semantic_lookup_ms
        )

    # 6. Search uploaded documents.
    retrieval_start = time.perf_counter()

    hybrid_results = search_chunks_hybrid(
        question=question,
        collection_id=collection_id,
        limit=10,
        candidate_limit=10,
    )

    retrieval_ms = (
        time.perf_counter() - retrieval_start
    ) * 1000

    metrics["retrieval_time_ms"] = retrieval_ms

    # 7. Rerank retrieved document chunks.
    rerank_start = time.perf_counter()

    reranked_chunks = rerank_chunks(
        question=question,
        chunks=hybrid_results,
        limit=RERANK_LIMIT,
    )

    rerank_ms = (
        time.perf_counter() - rerank_start
    ) * 1000

    metrics["rerank_time_ms"] = rerank_ms

    relevant_chunks = [
        chunk
        for chunk in reranked_chunks
        if chunk["rerank_score"] >= RERANK_SCORE_THRESHOLD
    ]

    # 8. If documents are insufficient, optionally search the web.
    if not relevant_chunks:

        if web_search_enabled:
            web_search_start = time.perf_counter()

            web_response = generate_web_answer(question)

            web_search_ms = (
                time.perf_counter() - web_search_start
            ) * 1000

            metrics["web_search_time_ms"] = web_search_ms

            response = {
                "answer": web_response["answer"],
                "sources": web_response["sources"],
            }

            # Cache the successful web answer in Redis.
            cache_write_start = time.perf_counter()

            cache_saved = set_cached_answer(
                cache_key=cache_key,
                response=response,
            )

            cache_write_ms = (
                time.perf_counter() - cache_write_start
            ) * 1000

            metrics["cache_write_time_ms"] = cache_write_ms

            # Store its embedding only if the Redis answer was saved.
            if cache_saved:
                save_semantic_cache_entry(
                    question=question,
                    embedding=embedding,
                    cache_key=cache_key,
                    collection_id=collection_id,
                    collection_version=collection_version,
                    web_search_enabled=web_search_enabled,
                )

            total_ms = (
                time.perf_counter() - request_start
            ) * 1000

            metrics["response_time_ms"] = total_ms

            logger.info(
                "RAG performance | result=web_fallback | "
                "web_search_ms=%.2f | total_ms=%.2f | "
                "cache_saved=%s",
                web_search_ms,
                total_ms,
                cache_saved,
            )

            return response

        # No relevant documents and web search is disabled.
        total_ms = (
            time.perf_counter() - request_start
        ) * 1000

        metrics["response_time_ms"] = total_ms

        logger.info(
            "RAG performance | result=insufficient_context | "
            "cache_lookup_ms=%.2f | retrieval_ms=%.2f | "
            "rerank_ms=%.2f | total_ms=%.2f",
            cache_lookup_ms,
            retrieval_ms,
            rerank_ms,
            total_ms,
        )

        return {
            "answer": INSUFFICIENT_CONTEXT,
            "sources": [],
        }

    # 9. Build context from relevant uploaded document chunks.
    context_parts = []
    sources = []
    seen_sources = set()

    for chunk in relevant_chunks:
        filename = chunk["filename"]
        page_number = chunk["page_number"]

        if page_number is not None:
            source_label = f"{filename}, Page {page_number}"
        else:
            source_label = filename

        context_parts.append(
            f"[Source: {source_label}]\n{chunk['text']}"
        )

        source_key = (
            chunk["document_id"],
            page_number,
        )

        if source_key not in seen_sources:
            sources.append({
                "source_type": "document",
                "document_id": chunk["document_id"],
                "filename": filename,
                "page_number": page_number,
            })

            seen_sources.add(source_key)

    context = "\n\n".join(context_parts)

    # 10. Generate answer using uploaded document context.
    generation_start = time.perf_counter()

    answer = generate_answer(
        question=question,
        context=context,
    )

    generation_ms = (
        time.perf_counter() - generation_start
    ) * 1000

    metrics["llm_time_ms"] = generation_ms

    response = {
        "answer": answer,
        "sources": sources,
    }

    # 11. Cache the document-based answer in Redis.
    cache_write_start = time.perf_counter()

    cache_saved = set_cached_answer(
        cache_key=cache_key,
        response=response,
    )

    cache_write_ms = (
        time.perf_counter() - cache_write_start
    ) * 1000

    metrics["cache_write_time_ms"] = cache_write_ms

    # Store the semantic entry only if Redis saved the answer.
    if cache_saved:
        save_semantic_cache_entry(
            question=question,
            embedding=embedding,
            cache_key=cache_key,
            collection_id=collection_id,
            collection_version=collection_version,
            web_search_enabled=web_search_enabled,
        )

    total_ms = (
        time.perf_counter() - request_start
    ) * 1000

    metrics["response_time_ms"] = total_ms

    logger.info(
        "RAG performance | result=cache_miss | "
        "cache_lookup_ms=%.2f | embedding_ms=%.2f | "
        "semantic_lookup_ms=%.2f | retrieval_ms=%.2f | "
        "rerank_ms=%.2f | generation_ms=%.2f | "
        "cache_write_ms=%.2f | total_ms=%.2f | "
        "cache_saved=%s",
        cache_lookup_ms,
        embedding_ms,
        metrics["semantic_cache_lookup_time_ms"],
        retrieval_ms,
        rerank_ms,
        generation_ms,
        cache_write_ms,
        total_ms,
        cache_saved,
    )

    return response
