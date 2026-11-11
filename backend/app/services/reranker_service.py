from sentence_transformers import CrossEncoder

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

reranker = CrossEncoder(MODEL_NAME)


def rerank_chunks(
    question: str,
    chunks: list[dict],
    limit: int = 5,
) -> list[dict]:
    """Rerank retrieved chunks using question-passage relevance."""

    if not chunks:
        return []

    pairs = [
        (question, chunk["text"])
        for chunk in chunks
    ]

    scores = reranker.predict(pairs)

    ranked_chunks = []

    for chunk, score in zip(chunks, scores):
        ranked_chunk = chunk.copy()
        ranked_chunk["rerank_score"] = float(score)
        ranked_chunks.append(ranked_chunk)

    ranked_chunks.sort(
        key=lambda chunk: chunk["rerank_score"],
        reverse=True,
    )

    return ranked_chunks[:limit]
