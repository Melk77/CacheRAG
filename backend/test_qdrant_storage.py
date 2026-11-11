
from app.services.document_processor import process_document
from app.services.embedding_service import generate_embeddings
from app.services.qdrant_service import store_chunks


# Real document information from PostgreSQL
DOCUMENT_ID = "05751485-2e89-46e7-b118-8e3eb6ed748d"
COLLECTION_ID = "92dd5e9c-3d04-420e-bba6-50bdcffdf61f"

FILE_PATH = (
    r"C:\Users\Hp\Desktop\Folder\CacheRAG\backend"
    r"\storage\documents\5d20a8ec-a51f-4b94-9548-26a4f221a872.pdf"
)

FILENAME = "chapter2.pdf"


# 1. Extract and chunk the PDF
chunks = process_document(
    file_path=FILE_PATH,
    document_id=DOCUMENT_ID,
    filename=FILENAME,
)

print("Total chunks:", len(chunks))


# 2. Generate embeddings for all chunks
texts = [chunk["text"] for chunk in chunks]
embeddings = generate_embeddings(texts)

print("Total embeddings:", len(embeddings))


# 3. Store chunks and embeddings in Qdrant
store_chunks(
    chunks=chunks,
    embeddings=embeddings,
    collection_id=COLLECTION_ID,
)

print("Document chunks stored in Qdrant successfully!")
