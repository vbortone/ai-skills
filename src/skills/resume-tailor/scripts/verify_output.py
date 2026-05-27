"""
Post-render verification for resume-tailor DOCX outputs.

Two compliance checks run after a build script renders a DOCX:

1. **Anonymization** — tokens the user has marked as never-publishable
   (e.g. an engagement client whose name must be replaced with a generic
   framing on every output) must not appear in the rendered DOCX.
   Patterns come from `tailor_config.json` in the user's working folder;
   if no config is found or the `anonymization` section is empty, this
   check is skipped with an informational note.
2. **Page count** — resumes are capped at 2 pages and cover letters at 1
   page. Render the DOCX to PDF via docx2pdf (MS Word COM automation),
   count pages with pypdf, fail loudly if over cap. Override with
   --no-strict-pages.

Library use
-----------
    from verify_output import (
        verify_anonymization,
        verify_page_count,
        load_config,
        find_config,
    )

    config = load_config(find_config([Path("Resume.docx").parent]))
    violations = verify_anonymization(Path("Resume.docx"), config=config)
    page_count = verify_page_count(Path("Resume.docx"), max_pages=2)

CLI use
-------
    python verify_output.py path/to/Resume.docx --max-pages 2
    python verify_output.py path/to/Resume.docx --config /path/to/tailor_config.json
    python verify_output.py path/to/Resume.docx --skip-anonymization
    python verify_output.py path/to/Resume.docx --no-strict-pages

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


CONFIG_FILENAME = "tailor_config.json"


class AnonymizationError(RuntimeError):
    """Raised when forbidden tokens are found in a rendered DOCX."""


class PageCountError(RuntimeError):
    """Raised when the rendered PDF exceeds the page cap."""


class ConfigError(RuntimeError):
    """Raised when tailor_config.json is malformed."""


@dataclass(frozen=True)
class ForbiddenToken:
    label: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class Violation:
    token: str
    match: str
    context: str

    def as_dict(self) -> dict:
        return {"token": self.token, "match": self.match, "context": self.context}


def find_config(search_paths: list[Path]) -> Path | None:
    """Walk up from each search path looking for `tailor_config.json`.

    Returns the first match found, or None. Each search path is walked
    independently; the function does not short-circuit between them."""
    for start in search_paths:
        current = start.resolve()
        if current.is_file():
            current = current.parent
        while True:
            candidate = current / CONFIG_FILENAME
            if candidate.is_file():
                return candidate
            if current.parent == current:
                break
            current = current.parent
    return None


def load_config(config_path: Path | None) -> dict:
    """Load and validate a tailor_config.json file. Returns {} when path is None."""
    if config_path is None:
        return {}
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read {config_path}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{config_path} is not valid JSON: {exc}") from exc


def _compile_forbidden_tokens(config: dict) -> list[ForbiddenToken]:
    anonymization = config.get("anonymization") or {}
    raw_tokens = anonymization.get("forbidden_tokens") or []
    compiled: list[ForbiddenToken] = []
    for entry in raw_tokens:
        if not isinstance(entry, dict):
            raise ConfigError(
                f"anonymization.forbidden_tokens entries must be objects, got {type(entry).__name__}"
            )
        label = entry.get("label")
        pattern = entry.get("pattern")
        if not label or not pattern:
            raise ConfigError(
                "anonymization.forbidden_tokens entries require both 'label' and 'pattern'"
            )
        try:
            compiled.append(ForbiddenToken(label=label, pattern=re.compile(pattern, re.IGNORECASE)))
        except re.error as exc:
            raise ConfigError(f"Invalid regex for token {label!r}: {exc}") from exc
    return compiled


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


def _find_violations_in_line(line: str, tokens: list[ForbiddenToken]) -> list[Violation]:
    out: list[Violation] = []
    for token in tokens:
        for m in token.pattern.finditer(line):
            start = max(0, m.start() - 30)
            end = min(len(line), m.end() + 30)
            snippet = line[start:end].strip()
            out.append(Violation(token=token.label, match=m.group(0), context=snippet))
    return out


def verify_anonymization(
    docx_path: Path,
    config: dict | None = None,
    skip: bool = False,
) -> list[Violation]:
    """Return the list of violations found in the DOCX. Empty list = clean.

    If skip is True, returns an empty list without scanning — the target
    JD is one of the configured exception employers and naming it is
    correct."""
    if skip:
        return []

    tokens = _compile_forbidden_tokens(config or {})
    if not tokens:
        return []

    violations: list[Violation] = []
    for line in _iter_docx_text(docx_path):
        violations.extend(_find_violations_in_line(line, tokens))
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
    config_path: Path | None,
    dash_normalizations_applied: int | None = None,
) -> dict:
    page_over_cap = (
        page_count is not None and max_pages is not None and page_count > max_pages
    )
    return {
        "docx_path": str(docx_path),
        "config_path": str(config_path) if config_path else None,
        "anonymization_violations": [v.as_dict() for v in violations],
        "page_count": page_count,
        "max_pages": max_pages,
        "page_over_cap": page_over_cap,
        "dash_normalizations_applied": dash_normalizations_applied,
        "passed": not violations and not page_over_cap,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("docx", help="Path to the rendered DOCX to verify.")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=(
            "Path to tailor_config.json. If omitted, the verifier walks up from "
            "the DOCX's parent directory looking for the file."
        ),
    )
    parser.add_argument(
        "--skip-anonymization",
        action="store_true",
        help=(
            "Skip the anonymization check (use when the target JD employer matches "
            "one of your configured anonymization patterns and naming them is correct)."
        ),
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

    config_path = args.config or find_config([docx_path.parent, Path.cwd()])
    config = load_config(config_path)

    if not args.skip_anonymization and not (config.get("anonymization") or {}).get(
        "forbidden_tokens"
    ):
        print(
            f"INFO: no anonymization patterns found "
            f"({'config absent' if config_path is None else f'config at {config_path}'}); "
            "anonymization check skipped.",
            file=sys.stderr,
        )

    violations = verify_anonymization(docx_path, config=config, skip=args.skip_anonymization)

    page_count: int | None = None
    if args.max_pages is not None:
        page_count = verify_page_count(docx_path, max_pages=args.max_pages)

    report = build_report(docx_path, violations, page_count, args.max_pages, config_path)
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
            "to use anonymized framing per your master_profile.md.",
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
