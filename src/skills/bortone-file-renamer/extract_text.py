#!/usr/bin/env python3
"""
extract_text.py — Extract text content from documents for the Bortone File Renamer skill.

Supports: PDF (text-based and scanned/image-only), DOCX, images (via OCR), and plain text files.

Usage:
    python extract_text.py <file_path>

Output goes to stdout. Errors go to stderr.
"""

import sys
import os

MAX_OUTPUT_CHARS = 10000


def extract_pdf(path: str) -> str:
    """Extract text from PDF. Falls back to OCR for image-only pages."""
    import fitz  # pymupdf

    doc = fitz.open(path)
    text_parts: list[str] = []
    ocr_pages: list[int] = []

    for i in range(len(doc)):
        page_text = doc[i].get_text().strip()
        if page_text:
            text_parts.append(page_text)
        else:
            ocr_pages.append(i)

    doc.close()

    # OCR any pages that had no extractable text
    if ocr_pages:
        try:
            ocr_text = _ocr_pdf_pages(path, ocr_pages)
            if ocr_text:
                text_parts.append(ocr_text)
        except Exception as e:
            print(f"Warning: OCR failed for image-only PDF pages: {e}", file=sys.stderr)

    return "\n".join(text_parts).strip()


def _ocr_pdf_pages(path: str, page_numbers: list[int]) -> str:
    """OCR specific pages of a PDF using pdf2image + pytesseract."""
    from pdf2image import convert_from_path
    import pytesseract

    text_parts: list[str] = []
    # Convert only the pages that need OCR (pdf2image uses 1-based page numbers)
    for page_num in page_numbers:
        images = convert_from_path(path, first_page=page_num + 1, last_page=page_num + 1)
        for img in images:
            page_text = pytesseract.image_to_string(img).strip()
            if page_text:
                text_parts.append(page_text)

    return "\n".join(text_parts)


def extract_docx(path: str) -> str:
    """Extract text from Word (.docx) documents."""
    from docx import Document

    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs).strip()


def extract_image(path: str) -> str:
    """Extract text from an image file using OCR."""
    from PIL import Image
    import pytesseract

    img = Image.open(path)
    return pytesseract.image_to_string(img).strip()


def extract_text_file(path: str) -> str:
    """Read plain text files."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().strip()


def truncate(text: str) -> str:
    """Truncate text to MAX_OUTPUT_CHARS with a notice."""
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n\n[... content truncated at 10,000 characters ...]"


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python extract_text.py <file_path>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(filepath)[1].lower()

    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".tiff", ".tif", ".bmp", ".webp"}
    text_extensions = {".txt", ".csv", ".md", ".html", ".htm", ".xml", ".json", ".rtf"}

    try:
        if ext == ".pdf":
            text = extract_pdf(filepath)
        elif ext == ".docx":
            text = extract_docx(filepath)
        elif ext == ".doc":
            print(
                "Warning: .doc (legacy Word) format has limited support. "
                "Consider converting to .docx for best results.",
                file=sys.stderr,
            )
            # Attempt to read as docx — may fail for true .doc files
            text = extract_docx(filepath)
        elif ext in image_extensions:
            text = extract_image(filepath)
        elif ext in text_extensions:
            text = extract_text_file(filepath)
        else:
            print(f"Error: Unsupported file type: {ext}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error extracting text from {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

    if not text:
        print("Warning: No text content could be extracted from this file.", file=sys.stderr)
        sys.exit(0)

    print(truncate(text))


if __name__ == "__main__":
    main()
