#!/usr/bin/env python3
"""
check_renames.py — Grade one eval run by inspecting the inbox folder after the skill ran.

Reads the eval's `checks` block from evals.json:
    present                regexes; each must match (re.search) at least one filename in the inbox
    absent                 regexes; none may match any filename in the inbox
    unchanged              {inbox filename: fixture path}; contents must be byte-identical
    date_is_file_creation  regex; the matching file's YYYY-MM-DD prefix must equal its creation date

Usage:
    python check_renames.py --eval-id <N> --dir <inbox folder> [--evals <evals.json>]

Output: one JSON object on stdout, in the skill-creator grading.json shape:
    {"eval_id": N, "passed": bool, "expectations": [{"text", "passed", "evidence"}]}

Exit codes: 0 all checks passed, 1 a check failed, 2 usage error (unknown eval id, missing dir).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(EVALS_DIR)
sys.path.insert(0, SKILL_DIR)
from classify import file_creation_date  # noqa: E402


def check(eval_def: dict, inbox: str) -> list[dict]:
    checks = eval_def.get("checks", {})
    names = sorted(os.listdir(inbox))
    results = []

    for pattern in checks.get("present", []):
        hits = [n for n in names if re.search(pattern, n)]
        results.append({"text": f"A file matching /{pattern}/ exists", "passed": bool(hits),
                        "evidence": f"matched {hits}" if hits else f"inbox has {names}"})

    for pattern in checks.get("absent", []):
        hits = [n for n in names if re.search(pattern, n)]
        results.append({"text": f"No file matches /{pattern}/", "passed": not hits,
                        "evidence": f"unexpected {hits}" if hits else "none matched"})

    for name, fixture in checks.get("unchanged", {}).items():
        path = os.path.join(inbox, name)
        with open(os.path.join(SKILL_DIR, fixture), "rb") as f:
            expected = f.read()
        if not os.path.exists(path):
            passed, evidence = False, f"{name} is missing"
        else:
            with open(path, "rb") as f:
                passed = f.read() == expected
            evidence = "contents identical to fixture" if passed else "contents differ from fixture"
        results.append({"text": f"{name} was not overwritten", "passed": passed, "evidence": evidence})

    pattern = checks.get("date_is_file_creation")
    if pattern:
        hits = [n for n in names if re.search(pattern, n)]
        if not hits:
            passed, evidence = False, f"no file matches /{pattern}/"
        else:
            created = file_creation_date(os.path.join(inbox, hits[0]))
            passed = hits[0].startswith(created)
            evidence = f"{hits[0]} vs creation date {created}"
        results.append({"text": "Undated document uses the file creation date", "passed": passed,
                        "evidence": evidence})
    return results


def load_eval(evals_path: str, eval_id: int) -> dict | None:
    with open(evals_path, encoding="utf-8") as f:
        return next((e for e in json.load(f)["evals"] if e["id"] == eval_id), None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Grade an eval run's inbox folder.")
    parser.add_argument("--eval-id", type=int, required=True)
    parser.add_argument("--dir", required=True, help="inbox folder after the run")
    parser.add_argument("--evals", default=os.path.join(EVALS_DIR, "evals.json"))
    args = parser.parse_args()

    eval_def = load_eval(args.evals, args.eval_id)
    if eval_def is None or not os.path.isdir(args.dir):
        print(f"Error: unknown eval id {args.eval_id} or missing dir {args.dir}", file=sys.stderr)
        sys.exit(2)

    results = check(eval_def, args.dir)
    passed = all(r["passed"] for r in results)
    json.dump({"eval_id": args.eval_id, "passed": passed, "expectations": results}, sys.stdout, indent=2)
    print()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
