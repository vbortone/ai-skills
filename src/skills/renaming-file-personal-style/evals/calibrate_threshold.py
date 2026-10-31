#!/usr/bin/env python3
"""
calibrate_threshold.py — Tune `review_confidence` against the user's own already-named paperwork.

Files the user already renamed by hand ({Date}_{Recipient}_{Sender}_{Topic}.{ext}) are labeled
data: the name is the right answer. This script samples them, copies each one to a temp folder
under a neutral name (doc_0001.pdf, so Jev can't read the answer off the file name), classifies
the copy, and compares each token with the label. The originals are only read, never renamed.

For each candidate threshold it reports, per token and per file:
  * review_rate      share flagged for review (the user's work)
  * accepted         number not flagged (would be auto-accepted)
  * accepted_wrong   accepted but different from the label (mistakes nobody reviews)
  * accepted_acc     share of accepted that match the label

Pick the lowest threshold whose accepted_wrong you can live with.

Usage:
    python calibrate_threshold.py --config <renamer_config.json> <dir_or_file> [...]
        [--sample N] [--seed S] [--thresholds 0.5,0.6,...] [--details] [--env-file <path>]

Directories are searched recursively. Labels are kept only when their recipient and topic are in
the config (older naming schemes are skipped and counted). Reads TYPESAFE_API_KEY from the
environment or evals/.env, like run_evals.py.

Output: one JSON object on stdout: {"model", "config_threshold", "labeled_found", "sampled",
"skipped", "errors", "thresholds": [...], "suggested", "files"? (with --details)}.
The output names the user's files, so keep it out of the repo.
Exit codes: 0 success, 1 usage or config error, 2 typesafe-sdk or TYPESAFE_API_KEY missing.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import sys
import tempfile

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(EVALS_DIR)
sys.path.insert(0, SKILL_DIR)
sys.path.insert(0, EVALS_DIR)
import classify  # noqa: E402
from run_evals import load_env_file  # noqa: E402

LABEL_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_([^_]+)_([^_]+)_([^_.]+)(?:_\d+)?(\.[A-Za-z0-9]+)$")
EXTENSIONS = {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
TOKENS = ("date", "recipient", "sender", "topic")
DEFAULT_THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
# Most useful threshold: the lowest one that keeps file-level accepted accuracy at or above this.
TARGET_ACCEPTED_ACC = 0.95


def find_labeled(paths: list[str], config: dict) -> tuple[list[tuple[str, dict]], int]:
    """Return ([(path, label)], count of names skipped because their tokens aren't in the config)."""
    recipients, topics = set(config["recipients"]), set(config["topics"])
    files: list[str] = []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
        for root, _, names in os.walk(p):
            files += [os.path.join(root, n) for n in names]
    labeled, skipped = [], 0
    for f in sorted(set(files)):
        m = LABEL_RE.match(os.path.basename(f))
        if not m or m.group(5).lower() not in EXTENSIONS:
            continue
        date, recipient, sender, topic, _ = m.groups()
        if recipient not in recipients or topic not in topics:
            skipped += 1
            continue
        labeled.append((f, {"date": date, "recipient": recipient, "sender": sender, "topic": topic}))
    return labeled, skipped


def same(name: str, got: str, want: str) -> bool:
    if name == "sender":  # hand-typed senders vary in case and punctuation: Bank-of-America vs Bank-Of-America
        return re.sub(r"[^a-z0-9]", "", got.lower()) == re.sub(r"[^a-z0-9]", "", want.lower())
    return got == want


def score(rows: list[dict], thresholds: list[float]) -> list[dict]:
    """Recompute review flags at each threshold from the stored probabilities."""
    out = []
    for t in thresholds:
        entry = {"threshold": t}
        for name in (*TOKENS, "file"):
            flagged = accepted = wrong = 0
            for r in rows:
                if name == "file":
                    review = any(_flag(r["tokens"][k], t) for k in TOKENS)
                    correct = all(r["match"].values())
                else:
                    review, correct = _flag(r["tokens"][name], t), r["match"][name]
                flagged += review
                if not review:
                    accepted += 1
                    wrong += not correct
            entry[name] = {"review_rate": round(flagged / len(rows), 3), "accepted": accepted,
                           "accepted_wrong": wrong,
                           "accepted_acc": round((accepted - wrong) / accepted, 3) if accepted else None}
        out.append(entry)
    return out


def _flag(tok: dict, threshold: float) -> bool:
    return tok["source"] != "jev" or tok["probability"] is None or tok["probability"] < threshold


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune review_confidence against already-named paperwork.")
    parser.add_argument("--config", required=True, help="the user's renamer_config.json")
    parser.add_argument("paths", nargs="+", help="folders (searched recursively) or files")
    parser.add_argument("--sample", type=int, default=40, help="files to classify (default 40; each is one API call)")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--thresholds", default=",".join(map(str, DEFAULT_THRESHOLDS)))
    parser.add_argument("--details", action="store_true", help="include per-file picks vs labels")
    parser.add_argument("--env-file", default=os.path.join(EVALS_DIR, ".env"))
    args = parser.parse_args()

    try:
        config = classify.load_config(args.config)
        thresholds = sorted(float(x) for x in args.thresholds.split(","))
    except (OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    load_env_file(args.env_file)
    try:
        from typesafe_sdk import TypeSafeClient
    except ImportError:
        print("Error: typesafe-sdk is not installed (pip install -r requirements.txt)", file=sys.stderr)
        sys.exit(2)
    if not os.environ.get("TYPESAFE_API_KEY", "").strip():
        print("Error: TYPESAFE_API_KEY is not set (evals/.env or the environment)", file=sys.stderr)
        sys.exit(2)

    labeled, skipped = find_labeled(args.paths, config)
    if not labeled:
        print("Error: no files named {Date}_{Recipient}_{Sender}_{Topic} with config recipients/topics", file=sys.stderr)
        sys.exit(1)
    sample = random.Random(args.seed).sample(labeled, min(args.sample, len(labeled)))

    rows, errors = [], []
    model = config.get("model", "jev-latest")
    work = tempfile.mkdtemp(prefix="rename-calibrate-")
    try:
        with TypeSafeClient(model=model, timeout=60.0) as client:
            for i, (path, label) in enumerate(sample, 1):
                copy = os.path.join(work, f"doc_{i:04d}{os.path.splitext(path)[1].lower()}")
                shutil.copyfile(path, copy)
                try:
                    r = classify.classify_file(client, copy, config, set())
                except Exception as e:  # noqa: BLE001 — one API failure shouldn't sink the run
                    r = {"error": f"classification failed: {e}"}
                finally:
                    os.remove(copy)
                if r.get("error"):
                    errors.append({"file": path, "error": r["error"]})
                    continue
                toks = r["tokens"]
                if toks["date"]["source"] == "file_created":  # the copy is brand new; production would use the original's date
                    toks["date"]["value"] = classify.file_creation_date(path)
                rows.append({"file": path, "label": label, "tokens": toks,
                             "match": {k: same(k, toks[k]["value"], label[k]) for k in TOKENS}})
                print(f"[{i}/{len(sample)}] {os.path.basename(path)}", file=sys.stderr)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if not rows:
        json.dump({"model": model, "errors": errors}, sys.stdout, indent=2)
        print()
        sys.exit(0)
    table = score(rows, thresholds)
    good = [e["threshold"] for e in table
            if e["file"]["accepted_acc"] is not None and e["file"]["accepted_acc"] >= TARGET_ACCEPTED_ACC]
    report = {
        "model": model,
        "config_threshold": float(config.get("review_confidence", 0.6)),
        "labeled_found": len(labeled),
        "skipped_other_scheme": skipped,
        "sampled": len(sample),
        "scored": len(rows),
        "errors": errors,
        "token_accuracy": {k: round(sum(r["match"][k] for r in rows) / len(rows), 3) for k in TOKENS},
        "thresholds": table,
        "suggested": {"threshold": min(good) if good else None,
                      "rule": f"lowest threshold with file-level accepted_acc >= {TARGET_ACCEPTED_ACC}"},
    }
    if args.details:
        report["files"] = [
            {"file": r["file"], "label": r["label"],
             "picked": {k: {"value": r["tokens"][k]["value"], "probability": r["tokens"][k]["probability"],
                            "source": r["tokens"][k]["source"]} for k in TOKENS},
             "mismatches": [k for k in TOKENS if not r["match"][k]]}
            for r in rows]
    json.dump(report, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
