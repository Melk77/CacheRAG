
from app.services.document_processor import extract_text_from_pdf

file_path = "storage/documents/5d20a8ec-a51f-4b94-9548-26a4f221a872.pdf"

pages = extract_text_from_pdf(file_path)

print("Total extracted pages:", len(pages))

for page in pages:
    print(f"\nPage {page['page_number']}:")
    print(page["text"][:300])
