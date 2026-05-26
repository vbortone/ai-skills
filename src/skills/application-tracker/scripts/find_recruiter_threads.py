"""
Search the user's recruiter file for threads mentioning a company.

The recruiters file is a single Markdown document the user maintains.
The skill does not enforce a specific structure — it scans for headings
or list items that mention the company name and returns the surrounding
markdown section for each match. The LLM extracts structured fields
(recruiter name, firm, last contact, comp anchor) from the excerpt at
runtime.

Usage
-----
    python find_recruiter_threads.py \\
        --company "Acme Corp" \\
        --recruiters-file "/path/to/memory/people/recruiters.md"

A "section" is the run of text from a heading (`# `, `## `, `### `,
`#### `) up to the next heading at the same or shallower level. The
script returns each section that mentions the company (case-insensitive,
whitespace/punctuation-tolerant) along with the heading text and its
line number.

Output is JSON on stdout.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class Match:
    heading: str
    heading_level: int
    line_number: int
    excerpt: str


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _split_sections(lines: list[str]) -> list[tuple[int, int, str, list[str]]]:
    """Return list of (start_line, heading_level, heading_text, body_lines).

    Each section runs from a heading up to the next heading of the same
    or shallower level. Pre-heading content (above the first heading) is
    returned as a synthetic section with level 0 / heading "".
    """
    sections: list[tuple[int, int, str, list[str]]] = []
    current_start = 0
    current_level = 0
    current_heading = ""
    current_body: list[str] = []

    for i, line in enumerate(lines):
        m = HEADING_PATTERN.match(line)
        if m:
            sections.append((current_start, current_level, current_heading, current_body))
            current_start = i + 1  # 1-indexed line numbers
            current_level = len(m.group(1))
            current_heading = m.group(2)
            current_body = []
        else:
            current_body.append(line)

    sections.append((current_start, current_level, current_heading, current_body))
    return sections


def _section_excerpt(heading: str, body_lines: list[str], max_chars: int = 600) -> str:
    body = "\n".join(line.rstrip() for line in body_lines).strip()
    text = f"## {heading}\n\n{body}" if heading else body
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "…"
    return text


def find_matches(text: str, company: str) -> list[Match]:
    lines = text.splitlines()
    sections = _split_sections(lines)
    company_norm = _normalize(company)
    matches: list[Match] = []
    for start_line, level, heading, body in sections:
        if not heading and not body:
            continue
        combined_norm = _normalize(heading + " " + " ".join(body))
        if company_norm and company_norm in combined_norm:
            matches.append(
                Match(
                    heading=heading,
                    heading_level=level,
                    line_number=start_line,
                    excerpt=_section_excerpt(heading, body),
                )
            )
    return matches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--company", required=True, help="Company name to search for (fuzzy match).")
    parser.add_argument(
        "--recruiters-file",
        required=True,
        type=Path,
        help="Path to the user's recruiters markdown file.",
    )
    args = parser.parse_args(argv)

    result: dict = {
        "company": args.company,
        "recruiters_file": str(args.recruiters_file),
        "matches": [],
        "warnings": [],
    }

    if not args.recruiters_file.is_file():
        result["warnings"].append(f"Recruiters file does not exist: {args.recruiters_file}")
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    try:
        text = args.recruiters_file.read_text(encoding="utf-8")
    except OSError as exc:
        result["warnings"].append(f"Could not read recruiters file: {exc}")
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    matches = find_matches(text, args.company)
    result["matches"] = [asdict(m) for m in matches]
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
