"""
Look up prior applications to a given company across active and
archived application folders.

Usage
-----
    python find_prior_applications.py \\
        --company "Acme Corp" \\
        --working-folder "/path/to/working-folder"

    # Override conventional paths if the user organizes things differently:
    python find_prior_applications.py \\
        --company "Acme Corp" \\
        --working-folder "/path/to/working-folder" \\
        --applications-dir "InFlight" \\
        --archive-dir "Closed"

Matching is case-insensitive and tolerant of whitespace / punctuation
variants — `"J.P. Morgan"`, `"jp morgan"`, `"JPMorgan"`, `"jp_morgan"`
all match a folder named `JPMorgan_Engineer_2025-06-01`.

For each match, if the folder contains an `_outcome.md` (archived) or a
`tailoring_notes.md` (active), the script returns a short excerpt
(first non-empty content paragraph after any frontmatter).

Output is JSON on stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_APPLICATIONS_DIR = "Applications"
DEFAULT_ARCHIVE_DIR = "Archive/Applications"

# Folder convention: {Company}_{Role}_{YYYY-MM-DD}
FOLDER_NAME_PATTERN = re.compile(
    r"^(?P<company>.+?)_(?P<role>.+?)_(?P<date>\d{4}-\d{2}-\d{2})(?:_v\d+)?$"
)


@dataclass(frozen=True)
class Match:
    folder: str
    status: str  # "active" or "archived"
    company_in_folder: str
    role: str
    date: str
    outcome_excerpt: str | None


def _normalize(s: str) -> str:
    """Collapse whitespace, punctuation, casing for fuzzy company-name matching."""
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _excerpt(text: str, max_chars: int = 400) -> str:
    """Extract the first non-empty content paragraph, ignoring YAML frontmatter."""
    body = text
    if body.startswith("---"):
        end = body.find("\n---", 3)
        if end != -1:
            body = body[end + 4 :]
    for chunk in re.split(r"\n\s*\n", body):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Skip pure heading lines
        if chunk.startswith("#") and "\n" not in chunk:
            continue
        if len(chunk) > max_chars:
            return chunk[:max_chars].rstrip() + "…"
        return chunk
    return ""


def _read_excerpt(folder: Path, status: str) -> str | None:
    """Return a short excerpt from _outcome.md (archived) or tailoring_notes.md (active)."""
    preferred = "_outcome.md" if status == "archived" else "tailoring_notes.md"
    fallback = "tailoring_notes.md" if status == "archived" else "_outcome.md"
    for candidate in (preferred, fallback):
        path = folder / candidate
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            excerpt = _excerpt(text)
            if excerpt:
                return excerpt
    return None


def _scan(directory: Path, status: str, company_norm: str) -> list[Match]:
    out: list[Match] = []
    if not directory.exists():
        return out
    for entry in directory.iterdir():
        if not entry.is_dir():
            continue
        match = FOLDER_NAME_PATTERN.match(entry.name)
        if not match:
            continue
        folder_company = match.group("company")
        if company_norm not in _normalize(folder_company):
            continue
        out.append(
            Match(
                folder=str(entry),
                status=status,
                company_in_folder=folder_company,
                role=match.group("role"),
                date=match.group("date"),
                outcome_excerpt=_read_excerpt(entry, status),
            )
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--company", required=True, help="Company name to search for (fuzzy match).")
    parser.add_argument(
        "--working-folder",
        required=True,
        type=Path,
        help="User's working folder containing the applications + archive directories.",
    )
    parser.add_argument(
        "--applications-dir",
        default=DEFAULT_APPLICATIONS_DIR,
        help=f"Active-applications directory, relative to --working-folder. Default: {DEFAULT_APPLICATIONS_DIR}",
    )
    parser.add_argument(
        "--archive-dir",
        default=DEFAULT_ARCHIVE_DIR,
        help=f"Archived-applications directory, relative to --working-folder. Default: {DEFAULT_ARCHIVE_DIR}",
    )
    args = parser.parse_args(argv)

    working_folder: Path = args.working_folder
    apps_dir = working_folder / args.applications_dir
    archive_dir = working_folder / args.archive_dir

    company_norm = _normalize(args.company)

    matches: list[Match] = []
    matches.extend(_scan(apps_dir, "active", company_norm))
    matches.extend(_scan(archive_dir, "archived", company_norm))
    matches.sort(key=lambda m: m.date, reverse=True)

    result = {
        "company": args.company,
        "applications_dir": str(apps_dir),
        "archive_dir": str(archive_dir),
        "matches": [asdict(m) for m in matches],
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
