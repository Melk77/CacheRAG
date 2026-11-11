
from pathlib import Path

import pymupdf

import re



def extract_text_from_pdf(file_path: str) -> list[dict]:
    extracted_pages = []

    with pymupdf.open(file_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text("text").strip()

            if text:
                extracted_pages.append(
                    {
                        "page_number": page_number,
                        "text": text,
                    }
                )

    return extracted_pages


def extract_text_from_txt(file_path: str) -> list[dict]:
    path = Path(file_path)

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    ).strip()

    if not text:
        return []

    return [
        {
            "page_number": None,
            "text": text,
        }
    ]


def clean_text(text: str) -> str:
    """
    Clean extracted text by normalizing whitespace.
    """
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 2000,
    chunk_overlap: int = 200,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    text = clean_text(text)

    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # Move the end to the nearest word boundary.
        if end < text_length:
            boundary = text.rfind(" ", start, end)

            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        # Calculate the next starting position with overlap.
        next_start = end - chunk_overlap

        # Move to the next word boundary.
        next_boundary = text.find(" ", next_start, end)

        if next_boundary != -1:
            next_start = next_boundary + 1

        start = next_start

    return chunks


def process_document(
    file_path: str,
    document_id: str,
    filename: str,
    chunk_size: int = 2000,
    chunk_overlap: int = 200,
) -> list[dict]:
    """
    Extract, clean, and chunk a PDF or TXT document.
    Preserve source metadata for every chunk.
    """
    path = Path(file_path)
    file_extension = path.suffix.lower()

    if file_extension == ".pdf":
        pages = extract_text_from_pdf(file_path)

    elif file_extension == ".txt":
        pages = extract_text_from_txt(file_path)

    else:
        raise ValueError("Only PDF and TXT files are supported")

    processed_chunks = []
    chunk_index = 0

    for page in pages:
        chunks = chunk_text(
            page["text"],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk in chunks:
            processed_chunks.append(
                {
                    "document_id": document_id,
                    "filename": filename,
                    "page_number": page["page_number"],
                    "chunk_index": chunk_index,
                    "text": chunk,
                }
            )

            chunk_index += 1

    return processed_chunks

