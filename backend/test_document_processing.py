
from app.services.document_processor import process_document

file_path = "storage/documents/5d20a8ec-a51f-4b94-9548-26a4f221a872.pdf"

chunks = process_document(
    file_path=file_path,
    document_id="test-document-001",
    filename="Formal Language Theory.pdf",
    chunk_size=2000,
    chunk_overlap=200,
)

print("Total chunks:", len(chunks))

for chunk in chunks[:3]:
    print("\nChunk metadata:")
    print("Document ID:", chunk["document_id"])
    print("Filename:", chunk["filename"])
    print("Page number:", chunk["page_number"])
    print("Chunk index:", chunk["chunk_index"])
    print("Text:", chunk["text"][:200])
