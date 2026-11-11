
from app.services.document_processor import clean_text, chunk_text

sample_text = """
CacheRAG is a document question-answering system.

It uses Retrieval-Augmented Generation to answer questions
using information from uploaded documents.

Redis improves performance by caching generated answers.
"""

cleaned = clean_text(sample_text)

chunks = chunk_text(
    cleaned,
    chunk_size=100,
    chunk_overlap=20,
)

print("Cleaned text:")
print(cleaned)

print("\nTotal chunks:", len(chunks))

for index, chunk in enumerate(chunks, start=1):
    print(f"\nChunk {index}:")
    print(chunk)
    print("Length:", len(chunk))
