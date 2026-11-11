from app.services.embedding_service import generate_embedding
from app.services.qdrant_service import search_chunks
from app.services.bm25_service import search_chunks_bm25


def search_chunks_hybrid(
    question: str,
    collection_id: str,
    limit: int = 5,
    candidate_limit: int = 10,
    rrf_k: int = 60,
) -> list[dict]:
    """
    Combine semantic and BM25 search results using
    Reciprocal Rank Fusion (RRF).
    """

    # 1. Run semantic search.
    semantic_results = search_chunks(
        query_embedding=generate_embedding(question),
        collection_id=collection_id,
        limit=candidate_limit,
    )

    # 2. Run BM25 keyword search.
    keyword_results = search_chunks_bm25(
        question=question,
        collection_id=collection_id,
        limit=candidate_limit,
    )

    # 3. Store combined results using a unique chunk identifier.
    combined_results = {}

    # 4. Calculate RRF scores for semantic results.
    for rank, result in enumerate(semantic_results, start=1):
        chunk_id = (
            result["document_id"],
            result["chunk_index"],
        )

        if chunk_id not in combined_results:
            combined_results[chunk_id] = {
                **result,
                "score": 0.0,
                "semantic_rank": None,
                "bm25_rank": None,
            }

        combined_results[chunk_id]["score"] += (
            1 / (rrf_k + rank)
        )
        combined_results[chunk_id]["semantic_rank"] = rank

    # 5. Add RRF scores from BM25 results.
    for rank, result in enumerate(keyword_results, start=1):
        chunk_id = (
            result["document_id"],
            result["chunk_index"],
        )

        if chunk_id not in combined_results:
            combined_results[chunk_id] = {
                **result,
                "score": 0.0,
                "semantic_rank": None,
                "bm25_rank": None,
            }

        combined_results[chunk_id]["score"] += (
            1 / (rrf_k + rank)
        )
        combined_results[chunk_id]["bm25_rank"] = rank

    # 6. Sort by the combined RRF score.
    ranked_results = sorted(
        combined_results.values(),
        key=lambda result: result["score"],
        reverse=True,
    )

    # 7. Return the highest-ranked chunks.
    return ranked_results[:limit]