
from app.services.embedding_service import generate_embedding, generate_embeddings

# Test one text
vector = generate_embedding("What is Retrieval-Augmented Generation?")

print("Single embedding dimensions:", len(vector))

# Test multiple texts
texts = [
    "Redis stores cached answers.",
    "Qdrant stores vector embeddings.",
]

vectors = generate_embeddings(texts)

print("Number of embeddings:", len(vectors))
print("Dimensions of each embedding:", [len(v) for v in vectors])
print("First five values:", vector[:5])
