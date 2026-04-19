#!/usr/bin/env python3
"""Tests for the renaming-file-personal-style extract_text.py script."""

import importlib.util
import os
import sys

import pytest

# Add the skill directory to the path so we can import the module directly
SKILL_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "skills", "renaming-file-personal-style")
)
sys.path.insert(0, SKILL_DIR)

import extract_text  # noqa: E402

FIXTURES = os.path.normpath(os.path.join(os.path.dirname(__file__), "fixtures"))

# Chandra OCR 2 is optional at test time — image OCR tests skip if it's not installed.
HAS_CHANDRA = importlib.util.find_spec("chandra") is not None


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
# Image OCR (requires Chandra OCR 2)
# ---------------------------------------------------------------------------

class TestImageExtraction:
    @pytest.mark.skipif(not HAS_CHANDRA, reason="Chandra OCR not installed")
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
