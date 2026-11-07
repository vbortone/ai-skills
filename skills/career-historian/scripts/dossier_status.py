"""
Coverage report over a local career-history directory of company dossiers.

Scans `--history-dir` for Markdown dossiers (every `*.md` except INDEX.md),
parses each dossier's frontmatter and section structure, and reports
per-company coverage: which sections exist, how many projects / skills /
contacts are captured, how many open questions remain, and when the
company was last interviewed. The interviewer uses this to build the
"what should we work on next" map without opening every dossier.

Read-only. Emits a single JSON object on stdout. Warnings (missing dir,
unparseable dossier) go into the JSON `warnings` list, not stderr, so the
caller always gets valid JSON.

Usage
-----
    python dossier_status.py --history-dir "/path/to/working-folder/career-history"

Exit codes
----------
    0 — report produced (possibly with warnings)
    2 — bad invocation (argparse error)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
OPEN_QUESTION_PATTERN = re.compile(r"^\s*[-*+]\s+\[ \]\s+\S")
TABLE_ROW_PATTERN = re.compile(r"^\s*\|.+\|\s*$")
TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|[\s:|-]+\|\s*$")

# Section titles the dossier template defines; matching is case-insensitive.
TEMPLATE_SECTIONS = [
    "Engagement context",
    "Projects",
    "Skills evidence",
    "Contacts",
    "Artifacts & sources ingested",
    "Open questions",
    "Interview log",
]


@dataclass
class DossierStatus:
    file: str
    company: str | None = None
    status: str | None = None
    start: str | None = None
    end: str | None = None
    last_interviewed: str | None = None
    sections_present: list[str] = field(default_factory=list)
    sections_missing: list[str] = field(default_factory=list)
    project_count: int = 0
    skill_count: int = 0
    contact_count: int = 0
    open_question_count: int = 0


def _parse_frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    """Return (flat key->value frontmatter, index of first body line).

    Only top-level `key: value` pairs are extracted; nested YAML (lists,
    maps) is skipped — the report needs scalars only and a YAML dependency
    isn't worth it for that."""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fm: dict[str, str] = {}
    for i in range(1, len(lines)):
        stripped = lines[i].strip()
        if stripped == "---":
            return fm, i + 1
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", lines[i])
        if m and m.group(2).strip():
            fm[m.group(1).lower()] = m.group(2).strip().strip("\"'")
    return {}, 0  # unterminated frontmatter — treat whole file as body


def _sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    """Map of level-2 section title (lowercased) -> (start, end) line range."""
    found: list[tuple[str, int]] = []
    for i, line in enumerate(lines):
        m = HEADING_PATTERN.match(line)
        if m and len(m.group(1)) == 2:
            found.append((m.group(2).strip().lower(), i))
    ranges: dict[str, tuple[int, int]] = {}
    for idx, (title, start) in enumerate(found):
        end = found[idx + 1][1] if idx + 1 < len(found) else len(lines)
        ranges[title] = (start + 1, end)
    return ranges


def _count_level3(lines: list[str], span: tuple[int, int]) -> int:
    count = 0
    for i in range(*span):
        m = HEADING_PATTERN.match(lines[i])
        if m and len(m.group(1)) == 3:
            count += 1
    return count


def _count_table_rows(lines: list[str], span: tuple[int, int]) -> int:
    """Data rows only: total pipe-rows minus one header and any separators."""
    rows = 0
    saw_header = False
    for i in range(*span):
        line = lines[i]
        if TABLE_SEPARATOR_PATTERN.match(line):
            continue
        if TABLE_ROW_PATTERN.match(line):
            if not saw_header:
                saw_header = True
                continue
            rows += 1
    return rows


def _count_open_questions(lines: list[str], span: tuple[int, int]) -> int:
    return sum(1 for i in range(*span) if OPEN_QUESTION_PATTERN.match(lines[i]))


def analyze_dossier(path: Path) -> DossierStatus:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    fm, body_start = _parse_frontmatter(lines)
    body = lines[body_start:]

    status = DossierStatus(
        file=str(path),
        company=fm.get("company"),
        status=fm.get("status"),
        start=fm.get("start"),
        end=fm.get("end"),
        last_interviewed=fm.get("last_interviewed"),
    )

    ranges = _sections(body)
    for section in TEMPLATE_SECTIONS:
        key = section.lower()
        if key in ranges:
            status.sections_present.append(section)
        else:
            status.sections_missing.append(section)

    if "projects" in ranges:
        status.project_count = _count_level3(body, ranges["projects"])
    if "contacts" in ranges:
        status.contact_count = _count_level3(body, ranges["contacts"])
    if "skills evidence" in ranges:
        status.skill_count = _count_table_rows(body, ranges["skills evidence"])
    if "open questions" in ranges:
        status.open_question_count = _count_open_questions(body, ranges["open questions"])

    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--history-dir",
        required=True,
        type=Path,
        help="Directory containing one Markdown dossier per company.",
    )
    args = parser.parse_args(argv)

    result: dict = {
        "history_dir": str(args.history_dir),
        "dossiers": [],
        "warnings": [],
    }

    if not args.history_dir.is_dir():
        result["warnings"].append(f"History directory does not exist: {args.history_dir}")
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    for md in sorted(args.history_dir.glob("*.md")):
        if md.name.upper() == "INDEX.MD":
            continue
        try:
            result["dossiers"].append(asdict(analyze_dossier(md)))
        except OSError as exc:
            result["warnings"].append(f"Could not read {md.name}: {exc}")

    if not result["dossiers"]:
        result["warnings"].append("No dossiers found (INDEX.md is excluded by design).")

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
