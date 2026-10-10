#!/usr/bin/env python3
"""
run_evals.py — Script-level evals for the renaming skill: classify, apply renames, grade.

For each eval in evals.json: copy its files into a fresh temp inbox, classify the files that
aren't already in {Date}_..._{Topic} form, apply every proposed rename (the evals pre-approve),
then grade the inbox with check_renames.check().

Modes:
    offline  No API key needed. Runs unit checks on candidate finding and sender normalization,
             then drives the full pipeline with a stub client that answers like a correct Jev.
             This verifies the code paths and the graders, not Jev's judgment.
    live     Runs the real classify.py CLI against TypeSafe (needs TYPESAFE_API_KEY). This is the
             eval of Jev's actual picks. Evals with `env.unset` run with those variables removed.

Usage:
    python run_evals.py --mode offline|live [--eval-id N ...] [--keep <dir>]

Output: one JSON object on stdout: {"mode", "passed", "failed", "skipped", "unit_checks", "evals"}.
Exit codes: 0 everything passed (skips allowed), 1 a check failed, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(EVALS_DIR)
CONFIG = os.path.join(EVALS_DIR, "files", "renamer_config.json")
sys.path.insert(0, SKILL_DIR)
sys.path.insert(0, EVALS_DIR)
import classify  # noqa: E402
from check_renames import check  # noqa: E402

ALREADY_NAMED = re.compile(r"^\d{4}-\d{2}-\d{2}_[^_]+_[^_]+_[^_]+(?:_\d+)?\.\w+$")

# What a correct Jev would pick for each fixture. Offline mode answers with these; the unit
# checks assert the code offers them as candidates and normalizes them as the evals expect.
TRUTH = {
    "statement_march.txt": {"date": "March 15, 2025", "date_iso": "2025-03-15", "ignored": "1980-01-01",
                            "sender": "BANK OF AMERICA", "sender_token": "Bank-of-America",
                            "recipient": "Alex", "topic": "Financial"},
    "irs_notice.txt": {"date": "January 20, 2025", "date_iso": "2025-01-20",
                       "sender": "Internal Revenue Service", "sender_token": "Internal-Revenue-Service",
                       "recipient": "Household", "topic": "Taxes"},
    "pge_bill.txt": {"date": "02/03/2025", "date_iso": "2025-02-03",
                     "sender": "PACIFIC GAS AND ELECTRIC COMPANY", "sender_token": "Pacific-Gas-and-Electric",
                     "recipient": "Sam", "topic": "Utility"},
    "bistro_receipt.txt": {"date": None, "date_iso": None,
                           "sender": "THE CORNER BISTRO", "sender_token": "The-Corner-Bistro",
                           "recipient": "Unknown", "topic": "Dining"},
}
EXTRA_SENDER_TOKENS = {"irs.gov": "IRS", "bankofamerica.com": "Bankofamerica", "Chase Bank USA, N.A.": "Chase-Bank-USA",
                       "Verizon Wireless Inc.": "Verizon-Wireless", "AT&T": "AT&T", "US TREASURY": "US-Treasury",
                       "Joe_Smith: Plumbing": "Joe-Smith-Plumbing", "CVS PHARMACY": "CVS-Pharmacy",
                       "PNC BANK, N.A.": "PNC-Bank", "THE HOME DEPOT": "The-Home-Depot"}


def result(text: str, passed: bool, evidence: str) -> dict:
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def unit_checks() -> list[dict]:
    config = classify.load_config(CONFIG)
    ignore = set(config["ignore_dates"])
    out = []
    for name, truth in TRUTH.items():
        with open(os.path.join(EVALS_DIR, "files", name), encoding="utf-8") as f:
            text = f.read()
        dates = classify.find_dates(text, ignore)
        if truth["date"]:
            out.append(result(f"{name}: document date '{truth['date']}' is a candidate parsed as {truth['date_iso']}",
                              dates.get(truth["date"]) == truth["date_iso"], f"candidates {dates}"))
        else:
            out.append(result(f"{name}: no date candidates (forces file-creation fallback)", not dates,
                              f"candidates {dates}"))
        if truth.get("ignored"):
            out.append(result(f"{name}: ignored date {truth['ignored']} is not offered", truth["ignored"] not in dates.values(),
                              f"candidates {dates}"))
        senders = classify.find_senders(text)
        out.append(result(f"{name}: sender '{truth['sender']}' is a candidate", truth["sender"] in senders,
                          f"candidates {senders}"))
        token = classify.sender_token(truth["sender"])
        out.append(result(f"{name}: '{truth['sender']}' normalizes to {truth['sender_token']}",
                          token == truth["sender_token"], f"got {token}"))
    for span, expected in EXTRA_SENDER_TOKENS.items():
        token = classify.sender_token(span)
        out.append(result(f"'{span}' normalizes to {expected}", token == expected, f"got {token}"))
    return out


class StubJev:
    """Answers each question with the TRUTH pick at 0.9 probability, the rest spread evenly."""

    def system_one(self, state, questions):
        from typesafe_sdk import SystemOneResponse

        truth = TRUTH[state["file_name"]]
        answers = {}
        for qid, question in questions.items():
            options = list(question.criteria)
            pick = truth.get(qid) if truth.get(qid) in options else classify.NONE
            rest = 0.1 / max(len(options) - 1, 1)
            answers[qid] = {"type": "choice", "choice": pick, "confidence": 0.9,
                            "probabilities": {o: 0.9 if o == pick else rest for o in options}}
        return SystemOneResponse.model_validate(
            {"model": "stub-jev", "answers": answers, "usage": {"input_tokens": 0, "output_tokens": 0}})


def classify_offline(paths: list[str]) -> tuple[int, dict]:
    config, claimed, client = classify.load_config(CONFIG), set(), StubJev()
    return 0, {"model": "stub-jev", "results": [classify.classify_file(client, p, config, claimed) for p in paths]}


def classify_live(paths: list[str], unset: list[str]) -> tuple[int, dict | None]:
    env = {k: v for k, v in os.environ.items() if k not in unset}
    proc = subprocess.run([sys.executable, os.path.join(SKILL_DIR, "classify.py"), "--config", CONFIG, *paths],
                          capture_output=True, text=True, env=env)
    return proc.returncode, json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else None


def run_eval(eval_def: dict, mode: str, keep: str | None) -> dict:
    unset = eval_def.get("env", {}).get("unset", [])
    summary = {"id": eval_def["id"], "name": eval_def["name"], "status": "ran"}
    if mode == "offline" and unset:
        return summary | {"status": "skipped", "reason": "env-dependent eval; covered by live mode"}
    if mode == "live" and "TYPESAFE_API_KEY" not in unset and not os.environ.get("TYPESAFE_API_KEY", "").strip():
        return summary | {"status": "skipped", "reason": "TYPESAFE_API_KEY not set"}

    inbox = tempfile.mkdtemp(prefix=f"rename-eval-{eval_def['id']}-")
    try:
        for rel in eval_def["files"]:
            shutil.copy(os.path.join(SKILL_DIR, rel), inbox)
        todo = sorted(os.path.join(inbox, n) for n in os.listdir(inbox) if not ALREADY_NAMED.match(n))
        code, output = classify_offline(todo) if mode == "offline" else classify_live(todo, unset)

        expectations = [result(f"classify.py exits {2 if unset else 0}", code == (2 if unset else 0), f"exit {code}")]
        proposals = []
        for r in (output or {}).get("results", []):
            proposals.append({"file": os.path.basename(r["file"]), "proposed": r.get("proposed_name"),
                              "needs_review": r.get("needs_review"), "error": r.get("error"),
                              "tokens": {k: {"value": t["value"], "probability": t["probability"]}
                                         for k, t in (r.get("tokens") or {}).items()}})
            if r.get("proposed_path") and not os.path.exists(r["proposed_path"]):
                os.rename(r["file"], r["proposed_path"])
        expectations += check(eval_def, inbox)
        summary |= {"passed": all(e["passed"] for e in expectations), "proposals": proposals,
                    "expectations": expectations}
        if keep:
            shutil.copytree(inbox, os.path.join(keep, f"eval-{eval_def['id']}-{eval_def['name']}"), dirs_exist_ok=True)
        return summary
    finally:
        shutil.rmtree(inbox, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the renaming skill's script-level evals.")
    parser.add_argument("--mode", choices=["offline", "live"], required=True)
    parser.add_argument("--eval-id", type=int, action="append", help="run only these ids (repeatable)")
    parser.add_argument("--keep", help="copy each finished inbox here for inspection")
    args = parser.parse_args()

    with open(os.path.join(EVALS_DIR, "evals.json"), encoding="utf-8") as f:
        evals = json.load(f)["evals"]
    if args.eval_id:
        evals = [e for e in evals if e["id"] in args.eval_id]
        if not evals:
            print(f"Error: no evals with ids {args.eval_id}", file=sys.stderr)
            sys.exit(2)

    units = unit_checks() if args.mode == "offline" else []
    runs = [run_eval(e, args.mode, args.keep) for e in evals]
    failed = sum(not u["passed"] for u in units) + sum(r.get("passed") is False for r in runs)
    report = {
        "mode": args.mode,
        "passed": sum(u["passed"] for u in units) + sum(r.get("passed") is True for r in runs),
        "failed": failed,
        "skipped": [r["id"] for r in runs if r["status"] == "skipped"],
        "unit_checks": units,
        "evals": runs,
    }
    json.dump(report, sys.stdout, indent=2)
    print()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
