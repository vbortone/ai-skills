#!/usr/bin/env python3
"""
extract_text.py — Extract text content from documents for the Bortone File Renamer skill.

Supports: PDF (text-based and scanned/image-only), DOCX, images (via OCR), and plain text files.
OCR is powered by Chandra OCR 2 (datalab-to/chandra-ocr-2) via HuggingFace transformers.

Usage:
    python extract_text.py <file_path>

Output goes to stdout. Errors go to stderr.
"""

import sys
import os
import re

MAX_OUTPUT_CHARS = 10000

_chandra_model = None


def _load_chandra():
    """Lazily load the Chandra OCR 2 model and processor (once per process)."""
    global _chandra_model
    if _chandra_model is None:
        from transformers import AutoModelForImageTextToText, AutoProcessor
        import torch

        has_cuda = torch.cuda.is_available()
        dtype = torch.bfloat16 if has_cuda else torch.float32

        model = AutoModelForImageTextToText.from_pretrained(
            "datalab-to/chandra-ocr-2",
            dtype=dtype,
            device_map="auto" if has_cuda else None,
        )
        model.eval()
        model.processor = AutoProcessor.from_pretrained("datalab-to/chandra-ocr-2")
        model.processor.tokenizer.padding_side = "left"
        _chandra_model = model
    return _chandra_model


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MD_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", re.MULTILINE)
_MD_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def _strip_markup(text: str) -> str:
    """Convert Chandra's markdown/HTML output into plain text."""
    text = _HTML_TAG_RE.sub(" ", text)
    text = _MD_TABLE_SEP_RE.sub("", text)
    text = text.replace("|", " ")
    text = _MD_HEADING_RE.sub("", text)
    text = _MULTI_BLANK_RE.sub("\n\n", text)
    return text


def _ocr_image(img) -> str:
    """Run Chandra OCR 2 on a PIL Image and return plain text."""
    from chandra.model.hf import generate_hf
    from chandra.model.schema import BatchInputItem
    from chandra.output import parse_markdown

    model = _load_chandra()
    batch = [BatchInputItem(image=img, prompt_type="ocr_layout")]
    result = generate_hf(batch, model)[0]
    markdown = parse_markdown(result.raw)
    return _strip_markup(markdown).strip()


def extract_pdf(path: str) -> str:
    """Extract text from PDF. Falls back to OCR for image-only pages."""
    import fitz  # pymupdf

    doc = fitz.open(path)
    text_parts: list[str] = []
    ocr_pages: list[int] = []

    for i in range(len(doc)):
        page_text = str(doc[i].get_text("text")).strip()
        if page_text:
            text_parts.append(page_text)
        else:
            ocr_pages.append(i)

    doc.close()

    if ocr_pages:
        try:
            ocr_text = _ocr_pdf_pages(path, ocr_pages)
            if ocr_text:
                text_parts.append(ocr_text)
        except Exception as e:
            print(f"Warning: OCR failed for image-only PDF pages: {e}", file=sys.stderr)

    return "\n".join(text_parts).strip()


def _ocr_pdf_pages(path: str, page_numbers: list[int]) -> str:
    """OCR specific pages of a PDF by rasterizing with pymupdf and running Chandra."""
    import io
    import fitz  # pymupdf
    from PIL import Image

    doc = fitz.open(path)
    text_parts: list[str] = []
    try:
        for page_num in page_numbers:
            pix = doc[page_num].get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            page_text = _ocr_image(img)
            if page_text:
                text_parts.append(page_text)
    finally:
        doc.close()

    return "\n".join(text_parts)


def extract_docx(path: str) -> str:
    """Extract text from Word (.docx) documents."""
    from docx import Document

    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs).strip()


def extract_image(path: str) -> str:
    """Extract text from an image file using Chandra OCR 2."""
    from PIL import Image

    return _ocr_image(Image.open(path))


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
