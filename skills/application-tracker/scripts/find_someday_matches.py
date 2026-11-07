"""
Scan the Someday section of a TASKS.md file for items matching keywords.

The user's TASKS.md is expected to contain a section (default: `Someday`)
of bullet-list items. The script returns items where any provided
keyword appears (case-insensitive, whole-word match by default).

Usage
-----
    python find_someday_matches.py \\
        --tasks-file "/path/to/TASKS.md" \\
        --keywords "healthcare,clinical,HIPAA"

    # Override the section heading if the user calls it something else:
    python find_someday_matches.py \\
        --tasks-file "/path/to/TASKS.md" \\
        --keywords "fintech,capital-markets" \\
        --section-heading "Backlog"

    # Substring match (default is whole-word):
    python find_someday_matches.py \\
        --tasks-file "/path/to/TASKS.md" \\
        --keywords "AI,ML" \\
        --substring

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
BULLET_PATTERN = re.compile(r"^(\s*)[-*+]\s+(.+?)\s*$")


@dataclass(frozen=True)
class Match:
    item: str
    matched_keywords: list[str]
    line_number: int


def _extract_section(text: str, section_heading: str) -> tuple[list[tuple[int, str]], int]:
    """Return (bullet items as (line_number, text), section_level) for the matching section.

    The section runs from the heading whose title matches `section_heading`
    (case-insensitive, exact match) up to the next heading at the same or
    shallower level."""
    lines = text.splitlines()
    target_norm = section_heading.strip().lower()
    section_start: int | None = None
    section_level: int = 0
    for i, line in enumerate(lines):
        m = HEADING_PATTERN.match(line)
        if m and m.group(2).strip().lower() == target_norm:
            section_start = i + 1
            section_level = len(m.group(1))
            break
    if section_start is None:
        return [], 0

    section_end = len(lines)
    for j in range(section_start, len(lines)):
        m = HEADING_PATTERN.match(lines[j])
        if m and len(m.group(1)) <= section_level:
            section_end = j
            break

    bullets: list[tuple[int, str]] = []
    for k in range(section_start, section_end):
        bm = BULLET_PATTERN.match(lines[k])
        if bm:
            bullets.append((k + 1, bm.group(2)))
    return bullets, section_level


def _match_keywords(item: str, keywords: list[str], substring: bool) -> list[str]:
    item_lower = item.lower()
    matched: list[str] = []
    for kw in keywords:
        kw_lower = kw.strip().lower()
        if not kw_lower:
            continue
        if substring:
            if kw_lower in item_lower:
                matched.append(kw)
        else:
            pattern = r"\b" + re.escape(kw_lower) + r"\b"
            if re.search(pattern, item_lower):
                matched.append(kw)
    return matched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--tasks-file",
        required=True,
        type=Path,
        help="Path to the user's tasks markdown file.",
    )
    parser.add_argument(
        "--keywords",
        required=True,
        help="Comma-separated keywords to match (case-insensitive).",
    )
    parser.add_argument(
        "--section-heading",
        default="Someday",
        help="Heading text of the section to scan. Default: Someday.",
    )
    parser.add_argument(
        "--substring",
        action="store_true",
        help="Match keywords as substrings (default is whole-word).",
    )
    args = parser.parse_args(argv)

    keywords = [kw.strip() for kw in args.keywords.split(",") if kw.strip()]

    result: dict = {
        "tasks_file": str(args.tasks_file),
        "section_heading": args.section_heading,
        "keywords": keywords,
        "matches": [],
        "warnings": [],
    }

    if not args.tasks_file.is_file():
        result["warnings"].append(f"Tasks file does not exist: {args.tasks_file}")
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    try:
        text = args.tasks_file.read_text(encoding="utf-8")
    except OSError as exc:
        result["warnings"].append(f"Could not read tasks file: {exc}")
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    bullets, _level = _extract_section(text, args.section_heading)
    if not bullets and "warnings" in result:
        result["warnings"].append(
            f"Section '{args.section_heading}' not found, or has no bullet items."
        )

    matches: list[Match] = []
    for line_no, item in bullets:
        matched_kw = _match_keywords(item, keywords, args.substring)
        if matched_kw:
            matches.append(Match(item=item, matched_keywords=matched_kw, line_number=line_no))

    result["matches"] = [asdict(m) for m in matches]
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
