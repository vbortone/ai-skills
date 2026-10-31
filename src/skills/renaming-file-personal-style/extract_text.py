#!/usr/bin/env python3
"""
extract_text.py — Read a document's text layer, or render its first page for Jev to read.

No local OCR. Digital documents (PDFs with a text layer, DOCX, plain text) are read as text.
Images and scanned PDFs have no text layer: `render_first_page()` turns them into a JPEG that
classify.py sends to TypeSafe's Jev, which reads the image itself. Everything here is pure pip
packages (PyMuPDF, python-docx), with no system installs such as Tesseract or Poppler.

Usage:
    python extract_text.py <file_path>              print the text layer
    python extract_text.py <file_path> --render <out.jpg>
                                                    write the page image Jev would see

Text goes to stdout, warnings and errors to stderr.
Exit codes: 0 success (including "no text layer"), 1 usage error, missing file, or extraction failure.
"""

import os
import sys

MAX_OUTPUT_CHARS = 10000
# A PDF with less text than this is treated as scanned: a stray page number or form label isn't enough to classify.
MIN_TEXT_CHARS = 40
# Jev rejects images with a side over 1568 px or under ~275 px ("400 Invalid image dimensions").
# Neither limit is documented; both were found by probing the API.
RENDER_MAX_SIDE = 1568
RENDER_MIN_SIDE = 280
JPEG_QUALITY = 85

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".tiff", ".tif", ".bmp", ".webp"}
TEXT_EXTENSIONS = {".txt", ".csv", ".md", ".html", ".htm", ".xml", ".json", ".rtf"}


class UnsupportedFileType(ValueError):
    """Raised when a file's extension has no extractor."""


def extract_pdf(path: str) -> str:
    """Text layer of every page. Scanned pages contribute nothing."""
    # Import as `pymupdf`: the legacy `fitz` alias prints a deprecation warning to stdout,
    # which corrupts the JSON that classify.py writes there.
    import pymupdf

    with pymupdf.open(path) as doc:
        return "\n".join(str(page.get_text("text")).strip() for page in doc).strip()


def extract_docx(path: str) -> str:
    """Extract text from Word (.docx) documents."""
    from docx import Document

    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs).strip()


def extract_text_file(path: str) -> str:
    """Read plain text files."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read().strip()


def extract(filepath: str) -> str:
    """Text layer of any supported file. Images return "" (Jev reads them as images)."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return extract_pdf(filepath)
    if ext == ".docx":
        return extract_docx(filepath)
    if ext == ".doc":
        print(
            "Warning: .doc (legacy Word) format has limited support. "
            "Consider converting to .docx for best results.",
            file=sys.stderr,
        )
        # Attempt to read as docx — may fail for true .doc files
        return extract_docx(filepath)
    if ext in IMAGE_EXTENSIONS:
        return ""
    if ext in TEXT_EXTENSIONS:
        return extract_text_file(filepath)
    raise UnsupportedFileType(f"Unsupported file type: {ext}")


def needs_image(filepath: str, text: str) -> bool:
    """True when Jev should read the page image instead of extracted text: images and scanned PDFs."""
    ext = os.path.splitext(filepath)[1].lower()
    return ext in IMAGE_EXTENSIONS or (ext == ".pdf" and len(text.strip()) < MIN_TEXT_CHARS)


def render_first_page(filepath: str, max_side: int = RENDER_MAX_SIDE, min_side: int = RENDER_MIN_SIDE) -> bytes:
    """Render the first page of a PDF, or an image file, to a JPEG that Jev accepts.

    Scales the long side to max_side. A page too narrow for that (a long receipt) is scaled so its
    short side is min_side instead and cropped to its top max_side pixels, where merchant and date sit.
    """
    import pymupdf

    with pymupdf.open(filepath) as doc:
        if not len(doc):
            raise ValueError("document has no pages")
        page = doc[0]
        rect = page.rect
        long_side, short_side = max(rect.width, rect.height), min(rect.width, rect.height)
        # One pixel of margin on each limit so rounding never lands outside them.
        zoom = (max_side - 1) / long_side
        if short_side * zoom < min_side + 1:
            zoom = (min_side + 1) / short_side
        span = (max_side - 1) / zoom  # page length that fits within max_side at this zoom
        clip = pymupdf.Rect(rect.x0, rect.y0, min(rect.x1, rect.x0 + span), min(rect.y1, rect.y0 + span))
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
        return pix.tobytes("jpeg", jpg_quality=JPEG_QUALITY)


def truncate(text: str) -> str:
    """Truncate text to MAX_OUTPUT_CHARS with a notice."""
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n\n[... content truncated at 10,000 characters ...]"


def main() -> None:
    args = sys.argv[1:]
    render_to = None
    if len(args) == 3 and args[1] == "--render":
        render_to = args[2]
        args = args[:1]
    if len(args) != 1:
        print("Usage: python extract_text.py <file_path> [--render <out.jpg>]", file=sys.stderr)
        sys.exit(1)

    filepath = args[0]
    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    try:
        if render_to:
            with open(render_to, "wb") as f:
                f.write(render_first_page(filepath))
            print(f"Wrote {render_to}", file=sys.stderr)
            return
        text = extract(filepath)
    except UnsupportedFileType as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error extracting text from {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

    if needs_image(filepath, text):
        print("Note: no usable text layer; classify.py sends this file to Jev as an image.", file=sys.stderr)
    if text:
        print(truncate(text))


if __name__ == "__main__":
    main()
