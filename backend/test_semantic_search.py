
from app.services.embedding_service import generate_embedding
from app.services.qdrant_service import search_chunks


COLLECTION_ID = "92dd5e9c-3d04-420e-bba6-50bdcffdf61f"

question = "What is the Chomsky hierarchy in formal language theory?"

# Convert the question into an embedding
query_embedding = generate_embedding(question)

# Search Qdrant
results = search_chunks(
    query_embedding=query_embedding,
    collection_id=COLLECTION_ID,
    limit=5,
)

print("\nQuestion:", question)
print("\nRetrieved chunks:", len(results))

for index, result in enumerate(results, start=1):
    print(f"\n--- Result {index} ---")
    print("Similarity score:", round(result["score"], 4))
    print("Filename:", result["filename"])
    print("Page:", result["page_number"])
    print("Text:", result["text"][:500])
