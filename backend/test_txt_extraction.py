
from app.services.document_processor import extract_text_from_txt

file_path = "storage/documents/test_document.txt"

pages = extract_text_from_txt(file_path)

print("Extracted content:")

for page in pages:
    print("Page number:", page["page_number"])
    print("Text:", page["text"])
