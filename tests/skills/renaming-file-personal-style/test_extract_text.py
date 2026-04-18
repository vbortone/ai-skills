#!/usr/bin/env python3
"""Tests for the renaming-file-personal-style extract_text.py script."""

import os
import sys
import shutil

import pytest

# Add the skill directory to the path so we can import the module directly
SKILL_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "skills", "renaming-file-personal-style")
)
sys.path.insert(0, SKILL_DIR)

import extract_text  # noqa: E402

FIXTURES = os.path.normpath(os.path.join(os.path.dirname(__file__), "fixtures"))

# Check if Tesseract is available for OCR tests
# On Windows, Tesseract may be installed but not on PATH
HAS_TESSERACT = shutil.which("tesseract") is not None or os.path.isfile(
    os.path.join(os.environ.get("PROGRAMFILES", ""), "Tesseract-OCR", "tesseract.exe")
)

# If Tesseract is installed but not on PATH, configure pytesseract to find it
if HAS_TESSERACT and not shutil.which("tesseract"):
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = os.path.join(
        os.environ.get("PROGRAMFILES", ""), "Tesseract-OCR", "tesseract.exe"
    )


# ---------------------------------------------------------------------------
# Text-based PDF
# ---------------------------------------------------------------------------

class TestPdfExtraction:
    def test_extracts_text_from_pdf(self):
        text = extract_text.extract_pdf(os.path.join(FIXTURES, "sample.pdf"))
        assert "Jennifer Bortone" in text
        assert "Bank of America" in text

    def test_pdf_contains_date(self):
        text = extract_text.extract_pdf(os.path.join(FIXTURES, "sample.pdf"))
        assert "February 10, 2025" in text


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------

class TestDocxExtraction:
    def test_extracts_text_from_docx(self):
        text = extract_text.extract_docx(os.path.join(FIXTURES, "sample.docx"))
        assert "Vincent and Jennifer Bortone" in text
        assert "Internal Revenue Service" in text

    def test_docx_contains_date(self):
        text = extract_text.extract_docx(os.path.join(FIXTURES, "sample.docx"))
        assert "January 5, 2025" in text

    def test_docx_contains_topic_hint(self):
        text = extract_text.extract_docx(os.path.join(FIXTURES, "sample.docx"))
        assert "Tax Return" in text


# ---------------------------------------------------------------------------
# Plain text files
# ---------------------------------------------------------------------------

class TestPlainTextExtraction:
    def test_extracts_text_from_txt(self):
        text = extract_text.extract_text_file(os.path.join(FIXTURES, "sample.txt"))
        assert "Vincent Bortone" in text
        assert "Chase Bank" in text

    def test_extracts_text_from_csv(self):
        text = extract_text.extract_text_file(os.path.join(FIXTURES, "sample.csv"))
        assert "Electric bill" in text


# ---------------------------------------------------------------------------
# Image OCR (requires Tesseract)
# ---------------------------------------------------------------------------

class TestImageExtraction:
    @pytest.mark.skipif(not HAS_TESSERACT, reason="Tesseract OCR not installed")
    def test_extracts_text_from_png(self):
        text = extract_text.extract_image(os.path.join(FIXTURES, "sample.png"))
        # OCR may not be perfect, check for key fragments
        text_lower = text.lower()
        assert "margaret" in text_lower or "invoice" in text_lower


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------

class TestTruncation:
    def test_large_text_is_truncated(self):
        text = "A" * 15000
        result = extract_text.truncate(text)
        assert "[... content truncated at 10,000 characters ...]" in result
        parts = result.split("\n\n[... content truncated at 10,000 characters ...]")
        assert len(parts[0]) == 10000

    def test_small_text_is_not_truncated(self):
        text = "Hello world"
        result = extract_text.truncate(text)
        assert result == "Hello world"
        assert "truncated" not in result

    def test_exact_limit_is_not_truncated(self):
        text = "B" * 10000
        result = extract_text.truncate(text)
        assert result == text
        assert "truncated" not in result


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_pdf_with_nonexistent_file_raises(self):
        with pytest.raises(Exception):
            extract_text.extract_pdf(os.path.join(FIXTURES, "nonexistent.pdf"))

    def test_docx_with_nonexistent_file_raises(self):
        with pytest.raises(Exception):
            extract_text.extract_docx(os.path.join(FIXTURES, "nonexistent.docx"))

    def test_text_file_with_nonexistent_file_raises(self):
        with pytest.raises(Exception):
            extract_text.extract_text_file(os.path.join(FIXTURES, "nonexistent.txt"))
