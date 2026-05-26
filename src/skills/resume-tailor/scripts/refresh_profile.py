"""
Check whether the master_profile.md is stale relative to other context
files in the user's working folder.

The skill treats master_profile.md as the canonical source of the user's
career data. Other files in the working folder (CLAUDE.md, memory/,
recruiter notes, project context, source exports) may carry updates the
profile hasn't absorbed yet. This helper walks the working folder and
reports any context-bearing file with an mtime newer than the profile's
`last_refreshed` frontmatter date.

Usage
-----
    python refresh_profile.py \\
        --profile-path "/path/to/master_profile.md"

    # By default, the working folder is the directory containing the
    # profile. Override with --working-folder.
    python refresh_profile.py \\
        --profile-path "/path/to/master_profile.md" \\
        --working-folder "/path/to/some-other-root"

    # Add directories the walker should also inspect (e.g. a network
    # share where source files live), and patterns to ignore.
    python refresh_profile.py \\
        --profile-path "/path/to/master_profile.md" \\
        --watch "/external/Source" \\
        --ignore "Drafts" --ignore "Old"

Outputs JSON to stdout describing the freshness state and any newer files.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from datetime import datetime
from pathlib import Path


CONTEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".docx"}

DEFAULT_IGNORE_NAMES = {
    "Applications",
    "Archive",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    ".DS_Store",
}


def parse_last_refreshed(profile_path: Path) -> datetime | None:
    """Read YAML frontmatter from master_profile.md and pull last_refreshed."""
    try:
        text = profile_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None

    if not text.startswith("---"):
        return None

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


def _should_skip(path: Path, ignores: set[str]) -> bool:
    name = path.name
    if name in ignores:
        return True
    if name.startswith("."):
        return True
    for pattern in ignores:
        if "*" in pattern or "?" in pattern:
            if fnmatch.fnmatch(name, pattern):
                return True
    return False


def walk_for_newer(
    roots: list[Path],
    threshold: datetime,
    profile_path: Path,
    ignores: set[str],
) -> list[dict]:
    """Walk each root recursively, returning context files with mtime > threshold.

    Skips the profile itself (it's the threshold reference), files in
    ignored directories, dotfiles, and files without a known context
    suffix."""
    seen: set[Path] = set()
    out: list[dict] = []
    profile_resolved = profile_path.resolve()

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved == profile_resolved:
                continue
            if resolved in seen:
                continue
            if any(_should_skip(part_path, ignores) for part_path in path.parents if part_path != root.parent):
                continue
            if path.suffix.lower() not in CONTEXT_SUFFIXES:
                continue
            seen.add(resolved)
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if mtime > threshold:
                out.append({
                    "path": str(path),
                    "name": path.name,
                    "mtime": mtime.isoformat(timespec="seconds"),
                    "delta_days": (mtime - threshold).days,
                })
    out.sort(key=lambda e: e["mtime"], reverse=True)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--profile-path",
        required=True,
        help="Path to master_profile.md.",
    )
    parser.add_argument(
        "--working-folder",
        default=None,
        help="Working folder to walk recursively. Defaults to the directory containing the profile.",
    )
    parser.add_argument(
        "--watch",
        action="append",
        default=[],
        help="Additional path to inspect (file or directory). Can be repeated.",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Additional directory/file name (or glob) to skip. Can be repeated.",
    )
    args = parser.parse_args(argv)

    profile_path = Path(args.profile_path)
    working_folder = Path(args.working_folder) if args.working_folder else profile_path.parent

    ignores = set(DEFAULT_IGNORE_NAMES) | set(args.ignore)
    roots: list[Path] = [working_folder]
    for extra in args.watch:
        roots.append(Path(extra))

    last = parse_last_refreshed(profile_path)
    result: dict = {
        "profile_path": str(profile_path),
        "working_folder": str(working_folder),
        "watched_paths": [str(r) for r in roots],
        "ignored_names": sorted(ignores),
        "last_refreshed": last.date().isoformat() if last else None,
        "stale": False,
        "newer_files": [],
        "warnings": [],
    }

    if last is None:
        result["warnings"].append(
            "Could not parse `last_refreshed` from master profile frontmatter — treating as stale."
        )
        result["stale"] = True
    elif not working_folder.exists():
        result["warnings"].append(f"Working folder does not exist: {working_folder}")
    else:
        newer = walk_for_newer(roots, last, profile_path, ignores)
        if newer:
            result["stale"] = True
            result["newer_files"] = newer

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
