"""
Post-render verification for resume-tailor DOCX outputs.

Two compliance checks run after a build script renders a DOCX:

1. **Anonymization** — tokens that identify Vincent's Big-4 client
   (PwC / PricewaterhouseCoopers / pwc.com) must not appear, per the
   skill's Anonymization Rule. Inversion: when the target JD is PwC
   itself, pass --allow-pwc / allow_pwc=True.
2. **Page count** — `ats_rules.md` caps resumes at 2 pages and
   `cover_letter_guide.md` caps cover letters at 1 page. Render the
   DOCX to PDF via docx2pdf (MS Word COM automation), count pages with
   pypdf, fail loudly if over cap. Override with --no-strict-pages.

Library use
-----------
    from verify_output import (
        verify_anonymization,
        verify_page_count,
        build_report,
    )

    violations = verify_anonymization(Path("Resume.docx"))
    page_count = verify_page_count(Path("Resume.docx"), max_pages=2)

CLI use
-------
    python verify_output.py path/to/Resume.docx --max-pages 2
    python verify_output.py path/to/Resume.docx --allow-pwc       # JD is PwC
    python verify_output.py path/to/Resume.docx --no-strict-pages # warn, don't fail

Exit codes
----------
    0 — all checks passed (or skipped via flags)
    1 — anonymization violation
    2 — page-count over cap (when strict)
    3 — both
    4 — input file missing
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from docx import Document


FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("PwC", re.compile(r"\bpwc\b", re.IGNORECASE)),
    ("pwc.com", re.compile(r"pwc\.com", re.IGNORECASE)),
    ("PricewaterhouseCoopers", re.compile(r"\bpricewaterhousecoopers\b", re.IGNORECASE)),
]


class AnonymizationError(RuntimeError):
    """Raised when forbidden tokens are found in a rendered DOCX."""


class PageCountError(RuntimeError):
    """Raised when the rendered PDF exceeds the page cap."""


@dataclass(frozen=True)
class Violation:
    token: str
    match: str
    context: str

    def as_dict(self) -> dict:
        return {"token": self.token, "match": self.match, "context": self.context}


def _iter_docx_text(docx_path: Path):
    """Yield every text-bearing string in the document: body paragraphs,
    table cells, and header/footer paragraphs. ATS-safe templates avoid
    headers/footers, but the check stays honest if one slips in."""
    doc = Document(str(docx_path))

    for para in doc.paragraphs:
        if para.text:
            yield para.text

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if para.text:
                        yield para.text

    for section in doc.sections:
        for container in (section.header, section.footer):
            for para in container.paragraphs:
                if para.text:
                    yield para.text


def _find_violations_in_line(line: str) -> list[Violation]:
    out: list[Violation] = []
    for token, pattern in FORBIDDEN_PATTERNS:
        for m in pattern.finditer(line):
            start = max(0, m.start() - 30)
            end = min(len(line), m.end() + 30)
            snippet = line[start:end].strip()
            out.append(Violation(token=token, match=m.group(0), context=snippet))
    return out


def verify_anonymization(docx_path: Path, allow_pwc: bool = False) -> list[Violation]:
    """Return the list of violations found in the DOCX. Empty list = clean.

    If allow_pwc is True, returns an empty list without scanning — the
    target employer is PwC and naming it is correct."""
    if allow_pwc:
        return []

    violations: list[Violation] = []
    for line in _iter_docx_text(docx_path):
        violations.extend(_find_violations_in_line(line))
    return violations


def count_pdf_pages(pdf_path: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(pdf_path)).pages)


def render_to_pdf(docx_path: Path, pdf_dir: Path | None = None) -> Path:
    """Convert a DOCX to PDF via docx2pdf (Word COM automation on Windows).

    Returns the PDF path. The PDF lives in pdf_dir if provided, otherwise
    alongside the DOCX. Callers using this for verification should pass a
    tempdir so the PDF gets cleaned up automatically."""
    from docx2pdf import convert

    out_dir = pdf_dir if pdf_dir is not None else docx_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / (docx_path.stem + ".pdf")
    convert(str(docx_path), str(pdf_path))
    if not pdf_path.is_file():
        raise PageCountError(
            f"docx2pdf did not produce a PDF at {pdf_path}. Is MS Word installed?"
        )
    return pdf_path


def verify_page_count(docx_path: Path, max_pages: int) -> int:
    """Render the DOCX to a temp PDF, count pages, return the count.

    Does not raise on overage — caller decides whether to enforce. Use the
    returned count against max_pages."""
    with tempfile.TemporaryDirectory(prefix="resume-tailor-pdf-") as tmpdir:
        pdf_path = render_to_pdf(docx_path, pdf_dir=Path(tmpdir))
        return count_pdf_pages(pdf_path)


def build_report(
    docx_path: Path,
    violations: list[Violation],
    page_count: int | None,
    max_pages: int | None,
) -> dict:
    page_over_cap = (
        page_count is not None and max_pages is not None and page_count > max_pages
    )
    return {
        "docx_path": str(docx_path),
        "anonymization_violations": [v.as_dict() for v in violations],
        "page_count": page_count,
        "max_pages": max_pages,
        "page_over_cap": page_over_cap,
        "passed": not violations and not page_over_cap,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("docx", help="Path to the rendered DOCX to verify.")
    parser.add_argument(
        "--allow-pwc",
        action="store_true",
        help="Skip the anonymization check (use when the target JD is PwC itself).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum allowed page count. Omit to skip the page-count check.",
    )
    parser.add_argument(
        "--no-strict-pages",
        action="store_true",
        help="Warn but don't fail on page-count overage.",
    )
    args = parser.parse_args(argv)

    docx_path = Path(args.docx)
    if not docx_path.is_file():
        print(f"ERROR: {docx_path} does not exist or is not a file.", file=sys.stderr)
        return 4

    violations = verify_anonymization(docx_path, allow_pwc=args.allow_pwc)

    page_count: int | None = None
    if args.max_pages is not None:
        page_count = verify_page_count(docx_path, max_pages=args.max_pages)

    report = build_report(docx_path, violations, page_count, args.max_pages)
    print(json.dumps(report, indent=2))

    exit_code = 0
    if violations:
        exit_code |= 1
        print(
            f"\nERROR: {len(violations)} anonymization violation(s) in {docx_path.name}:",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  - {v.token!r} matched {v.match!r} near: {v.context!r}", file=sys.stderr)
        print(
            "\nFix the source content (resume JSON, cover letter JSON, or recruiter pitch) "
            "to use anonymized framing per memory/glossary.md.",
            file=sys.stderr,
        )

    if report["page_over_cap"]:
        msg = (
            f"\n{'ERROR' if not args.no_strict_pages else 'WARN'}: "
            f"{docx_path.name} rendered to {page_count} pages, cap is {args.max_pages}."
        )
        print(msg, file=sys.stderr)
        if not args.no_strict_pages:
            exit_code |= 2

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
