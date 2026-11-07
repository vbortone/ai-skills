"""
Move an application folder from Applications/ to Archive/Applications/
and stub an _outcome.md if one doesn't already exist.

The script does NOT silently mutate the user's curated context files
(TASKS.md, recruiters file, job-search memory). It returns a JSON
report listing follow-up nudges so the LLM or user can apply those
updates explicitly.

Usage
-----
    python archive_application.py \\
        --application-folder "/path/to/Applications/Globant_VP_Technology_2026-05-16" \\
        --working-folder "/path/to/working-folder"

    # With outcome fields pre-populated:
    python archive_application.py \\
        --application-folder "..." \\
        --working-folder "..." \\
        --outcome-status "Rejected" \\
        --outcome-notes "Not quite the right fit." \\
        --notified-by "Nicole Gruber, Executive Recruiting Partner — Globant"

    # Dry-run shows what would happen without moving anything:
    python archive_application.py \\
        --application-folder "..." \\
        --working-folder "..." \\
        --dry-run

Output is JSON on stdout.

Exit codes
----------
    0 — moved successfully (or dry-run completed)
    1 — destination already exists; refuse to clobber
    2 — application folder is not inside the working folder's
        Applications/ directory
    3 — application folder does not exist
    4 — other I/O error
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_APPLICATIONS_DIR = "Applications"
DEFAULT_ARCHIVE_DIR = "Archive/Applications"
OUTCOME_FILENAME = "_outcome.md"


OUTCOME_TEMPLATE = """# Outcome — {folder_name}

**Status:** {status}
**Decision date:** {decision_date}
**Notified by:** {notified_by}
**Your read:** {your_read}

## What happened

{notes}

## Lessons

- {lesson_placeholder}

## Follow-ups

- [ ] {followup_placeholder}
"""


def _within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _stub_outcome(
    folder: Path,
    folder_name: str,
    status: str,
    decision_date: str,
    notified_by: str,
    notes: str,
    your_read: str,
) -> tuple[Path, bool]:
    """Create _outcome.md inside folder if it doesn't exist.

    Returns (path, created) — created=False if the file already existed."""
    path = folder / OUTCOME_FILENAME
    if path.exists():
        return path, False
    body = OUTCOME_TEMPLATE.format(
        folder_name=folder_name,
        status=status or "{Rejected / Withdrew / No response / Hired — pick one}",
        decision_date=decision_date or "{YYYY-MM-DD}",
        notified_by=notified_by or "{Name, Title — Company / Firm}",
        your_read=your_read or "{one-line summary in your own voice}",
        notes=notes or "{A few paragraphs of detail — what stage, what feedback, what signals.}",
        lesson_placeholder="{Concrete things to do differently next time.}",
        followup_placeholder="{Anything to do as a result — keep in touch with the recruiter, revisit in 6 months, etc.}",
    )
    path.write_text(body, encoding="utf-8")
    return path, True


def _follow_ups(working_folder: Path, folder_name: str) -> list[str]:
    """Return a list of human-readable nudges for the user / LLM.

    The script intentionally does not mutate these files itself —
    they're user-curated and the right edits depend on each user's
    conventions."""
    out: list[str] = []
    tasks_file = working_folder / "TASKS.md"
    if tasks_file.is_file():
        out.append(
            f"Update {tasks_file.name}: move any Active task referencing this application to Done."
        )
    js_file = working_folder / "memory" / "projects" / "job-search.md"
    if js_file.is_file():
        out.append(
            f"Update {js_file.relative_to(working_folder)}: move {folder_name} from active to closed; "
            f"populate the outcome row."
        )
    recruiter_file = working_folder / "memory" / "people" / "recruiters.md"
    if recruiter_file.is_file():
        out.append(
            f"Update {recruiter_file.relative_to(working_folder)}: mark the relevant thread closed/lapsed if applicable."
        )
    out.append(
        f"Fill in the placeholder fields in {OUTCOME_FILENAME} — the first content paragraph is what "
        f"find_prior_applications.py returns when another tailoring run hits the same company."
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--application-folder",
        required=True,
        type=Path,
        help="Path to the application folder to archive.",
    )
    parser.add_argument(
        "--working-folder",
        required=True,
        type=Path,
        help="The user's working folder (root containing Applications/ and Archive/).",
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
    parser.add_argument(
        "--outcome-status",
        default="",
        help="Outcome status (Rejected / Withdrew / No response / Hired). Optional.",
    )
    parser.add_argument(
        "--outcome-notes",
        default="",
        help="Free-text notes for the 'What happened' section. Optional.",
    )
    parser.add_argument(
        "--notified-by",
        default="",
        help="Who notified you of the outcome (name + title + firm). Optional.",
    )
    parser.add_argument(
        "--your-read",
        default="",
        help="One-line summary in your own voice. Optional.",
    )
    parser.add_argument(
        "--decision-date",
        default="",
        help="Date of the outcome decision (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without moving anything.",
    )
    args = parser.parse_args(argv)

    app_folder: Path = args.application_folder
    working_folder: Path = args.working_folder
    applications_root = working_folder / args.applications_dir
    archive_root = working_folder / args.archive_dir

    if not app_folder.exists():
        print(
            json.dumps({"error": f"application folder does not exist: {app_folder}"}, indent=2),
            file=sys.stderr,
        )
        return 3

    if not _within(app_folder, applications_root):
        print(
            json.dumps(
                {
                    "error": (
                        f"application folder is not inside the working folder's "
                        f"applications directory ({applications_root})."
                    )
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2

    folder_name = app_folder.name
    dest_folder = archive_root / folder_name

    if dest_folder.exists():
        print(
            json.dumps(
                {
                    "error": (
                        f"destination already exists: {dest_folder}. Refusing to clobber. "
                        f"Move it aside or remove it first."
                    )
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    decision_date = args.decision_date or datetime.now(timezone.utc).date().isoformat()

    report: dict = {
        "dry_run": args.dry_run,
        "moved_from": str(app_folder),
        "moved_to": str(dest_folder),
        "folder_name": folder_name,
        "outcome_file": str(dest_folder / OUTCOME_FILENAME),
        "outcome_status": args.outcome_status or None,
        "outcome_stubbed": False,
        "follow_ups": _follow_ups(working_folder, folder_name),
    }

    if args.dry_run:
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    try:
        archive_root.mkdir(parents=True, exist_ok=True)
        shutil.move(str(app_folder), str(dest_folder))
    except OSError as exc:
        print(json.dumps({"error": f"move failed: {exc}"}, indent=2), file=sys.stderr)
        return 4

    outcome_path, created = _stub_outcome(
        dest_folder,
        folder_name=folder_name,
        status=args.outcome_status,
        decision_date=decision_date,
        notified_by=args.notified_by,
        notes=args.outcome_notes,
        your_read=args.your_read,
    )
    report["outcome_file"] = str(outcome_path)
    report["outcome_stubbed"] = created

    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
