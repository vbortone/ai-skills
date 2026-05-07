"""
Check whether the master_profile.md is stale relative to the user's
Source folder. Stale = at least one source file has an mtime newer than
the profile's last_refreshed date.

Usage
-----
    python refresh_profile.py \\
        --source-dir "/path/to/Source" \\
        --profile-path "/path/to/master_profile.md"

Outputs JSON to stdout describing the freshness state and any newer files,
e.g.:
    {
      "stale": true,
      "last_refreshed": "2026-05-06",
      "newer_files": [
        {"path": "...", "mtime": "2026-05-08T14:23:11", "delta_days": 2}
      ]
    }
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def parse_last_refreshed(profile_path: Path) -> datetime | None:
    """Read YAML frontmatter from master_profile.md and pull last_refreshed."""
    try:
        text = profile_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None

    if not text.startswith("---"):
        return None

    # Slice to the second '---'
    end = text.find("---", 3)
    if end == -1:
        return None
    front = text[3:end]

    match = re.search(r"^last_refreshed:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*$", front, re.MULTILINE)
    if not match:
        return None
    try:
        return datetime.fromisoformat(match.group(1))
    except ValueError:
        return None


def newer_files(source_dir: Path, threshold: datetime) -> list[dict]:
    """Return source files with mtime > threshold."""
    out: list[dict] = []
    if not source_dir.exists():
        return out
    for entry in source_dir.iterdir():
        if entry.is_file():
            mtime = datetime.fromtimestamp(entry.stat().st_mtime)
            if mtime > threshold:
                out.append({
                    "path": str(entry),
                    "name": entry.name,
                    "mtime": mtime.isoformat(timespec="seconds"),
                    "delta_days": (mtime - threshold).days,
                })
    out.sort(key=lambda e: e["mtime"], reverse=True)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--source-dir", required=True, help="Path to user's Source folder.")
    parser.add_argument("--profile-path", required=True, help="Path to master_profile.md.")
    args = parser.parse_args(argv)

    profile_path = Path(args.profile_path)
    source_dir = Path(args.source_dir)

    last = parse_last_refreshed(profile_path)
    result: dict = {
        "stale": False,
        "last_refreshed": last.date().isoformat() if last else None,
        "newer_files": [],
        "warnings": [],
    }

    if last is None:
        result["warnings"].append("Could not parse last_refreshed from master profile frontmatter.")
        result["stale"] = True
    elif not source_dir.exists():
        result["warnings"].append(f"Source directory does not exist: {source_dir}")
    else:
        newer = newer_files(source_dir, last)
        if newer:
            result["stale"] = True
            result["newer_files"] = newer

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
