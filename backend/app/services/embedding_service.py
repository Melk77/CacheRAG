
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

model = SentenceTransformer(MODEL_NAME)


def generate_embedding(text: str) -> list[float]:
    """Convert one text string into a 384-dimensional vector."""
    embedding = model.encode(text, normalize_embeddings=True)

    return embedding.tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Convert multiple text strings into embedding vectors."""
    embeddings = model.encode(texts, normalize_embeddings=True)

    return embeddings.tolist()
