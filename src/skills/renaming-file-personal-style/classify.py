#!/usr/bin/env python3
"""
classify.py — Propose {Date}_{Recipient}_{Sender}_{Topic}.{ext} names with TypeSafe's Jev model.

Jev picks answers but does not write them. For each file:

  * Date      — code finds every date-shaped span and parses it; Jev picks which span is the
                document's own date. Code converts it to YYYY-MM-DD and drops dates listed in
                `ignore_dates`. Falls back to the file's creation date.
  * Sender    — code finds capitalized name phrases and web/email domains; Jev picks the issuing
                organization. Code turns the pick into the dashed filename form.
  * Recipient — Jev picks one entry from the config's `recipients` roster.
  * Topic     — Jev picks one entry from the config's `topics` list.

All four questions go to Jev together in one request per file.

Usage:
    python classify.py --config <renamer_config.json> <file> [<file> ...]

Requires the TYPESAFE_API_KEY environment variable (https://console.typesafe.ai/).
The config file holds the user's own recipients, topics and ignored dates; see
examples/renamer_config.json for the shape.

Output: one JSON object on stdout:
    {"model": "...", "results": [{"file", "proposed_name", "proposed_path", "needs_review",
                                  "tokens": {"date", "recipient", "sender", "topic"}, "error"}]}
Each token carries its `value`, `source`, the probability Jev gave it, Jev's `confidence`,
the runner-up `alternatives`, and `needs_review`.

Exit codes:
    0  success (per-file failures are reported in results[].error)
    1  usage or config error
    2  typesafe-sdk not installed or TYPESAFE_API_KEY not set
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_text import extract  # noqa: E402

NONE = "none"
MAX_OPTIONS = 250  # Choice allows 255 options; leave room for the NONE option
STATE_CHARS = 6000  # Jev loses accuracy on large, irrelevant state; the head of a document carries the naming facts
SENDER_HEAD_CHARS = 4000  # letterheads sit at the top...
SENDER_TAIL_CHARS = 1500  # ...and legal footers at the bottom

# --- Date candidates ---------------------------------------------------------------------------

MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
            ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
            ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"), ("dec", "december"),
        ],
        start=1,
    )
    for m in names
}
_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))

DATE_PATTERNS = [
    # 2025-03-15
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), ("y", "m", "d")),
    # 03/15/2025, 3-15-25, 03.15.2025 (US month-first)
    (re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}|\d{2})\b"), ("m", "d", "y")),
    # March 15, 2025 / Mar. 15th 2025
    (re.compile(rf"\b({_MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I), ("mon", "d", "y")),
    # 15 March 2025
    (re.compile(rf"\b(\d{{1,2}})\s+({_MONTH_RE})\.?,?\s+(\d{{4}})\b", re.I), ("d", "mon", "y")),
]


def find_dates(text: str, ignore: set[str]) -> dict[str, str]:
    """Return {verbatim span: ISO date} in document order, minus ignored and implausible dates."""
    latest_year = dt.date.today().year + 5
    hits: list[tuple[int, str, str]] = []
    for pattern, order in DATE_PATTERNS:
        for match in pattern.finditer(text):
            parts = dict(zip(order, match.groups()))
            try:
                year = int(parts["y"])
                if year < 100:
                    year += 2000 if year < 70 else 1900
                month = MONTHS[parts["mon"].lower()] if "mon" in parts else int(parts["m"])
                day = int(parts["d"])
                iso = dt.date(year, month, day).isoformat()
            except (ValueError, KeyError):
                continue
            if iso in ignore or not 1900 <= year <= latest_year:
                continue
            hits.append((match.start(), match.group(0).strip(), iso))
    found: dict[str, str] = {}
    for _, span, iso in sorted(hits):
        found.setdefault(span, iso)
    return dict(list(found.items())[:MAX_OPTIONS])


def file_creation_date(path: str) -> str:
    st = os.stat(path)
    # st_birthtime exists on macOS/Windows (py3.12+); st_ctime is creation time on Windows.
    ts = getattr(st, "st_birthtime", None) or (st.st_ctime if os.name == "nt" else st.st_mtime)
    return dt.date.fromtimestamp(ts).isoformat()


# --- Sender candidates -------------------------------------------------------------------------

_WORD = r"[A-Z][A-Za-z0-9&'.\-]*"
NAME_RE = re.compile(rf"{_WORD}(?:[ \t]+(?:(?:of|and|&|the|for|de)[ \t]+)?{_WORD}){{0,5}}")
DOMAIN_RE = re.compile(r"\b(?:www\.|[\w.+-]+@)?([a-z0-9][a-z0-9-]*)\.(?:com|org|net|gov|edu|us|co|io|bank)\b", re.I)
NOT_SENDERS = {m.capitalize() for m in MONTHS} | {
    "Page", "Date", "Total", "Amount", "Account", "Balance", "Statement", "Dear", "Sincerely",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "PO", "P.O.", "Box",
}


def find_senders(text: str) -> list[str]:
    """Candidate sender names, letterhead first, deduped case-insensitively."""
    region = text[:SENDER_HEAD_CHARS]
    if len(text) > SENDER_HEAD_CHARS:
        region += "\n" + text[-SENDER_TAIL_CHARS:]
    hits: list[tuple[int, str]] = []
    for match in NAME_RE.finditer(region):
        span = match.group(0).strip(" .,-'&")
        if len(span) >= 2 and span not in NOT_SENDERS and not span.isdigit():
            hits.append((match.start(), span))
    for match in DOMAIN_RE.finditer(region):
        hits.append((match.start(), re.sub(r"^www\.", "", match.group(0).split("@")[-1].lower())))
    seen: set[str] = set()
    out: list[str] = []
    for _, span in sorted(hits):
        if span.lower() not in seen:
            seen.add(span.lower())
            out.append(span)
    return out[:MAX_OPTIONS]


CORPORATE_SUFFIX_RE = re.compile(
    r"[,\s]+(?:inc|incorporated|llc|l\.l\.c|corp|corporation|co|company|ltd|limited|n\.a|p\.c|plc)\.?$", re.I
)
SMALL_WORDS = {"of", "and", "the", "for", "de"}


def sender_token(span: str) -> str:
    """Normalize a picked sender span into the filename form, e.g. 'BANK OF AMERICA, N.A.' -> 'Bank-of-America'."""
    name = span
    domain = DOMAIN_RE.fullmatch(name)
    if domain:
        name = domain.group(1)
        name = name.upper() if len(name) <= 4 else name.capitalize()
    while True:
        stripped = CORPORATE_SUFFIX_RE.sub("", name).strip(" ,.")
        if stripped == name or not stripped:
            break
        name = stripped
    shouted = name.isupper() and " " in name  # 'BANK OF AMERICA' letterheads, but leave 'IRS' / 'AT&T' alone
    words = []
    for i, word in enumerate(name.split()):
        if word.lower() in SMALL_WORDS:
            words.append(word.lower() if i else word.capitalize())
        elif shouted and len(word) > 2 and re.search(r"[AEIOU]", word):  # keep vowel-less acronyms: CVS, PNC
            words.append(word.capitalize())
        else:
            words.append(word)
    name = "-".join(words)
    name = re.sub(r'[\\/:*?"<>|_\s]+', "-", name)  # filename-unsafe chars and the token separator
    return re.sub(r"-{2,}", "-", name).strip("-.") or "Unknown"


# --- Jev ---------------------------------------------------------------------------------------


def build_questions(config: dict, dates: dict[str, str], senders: list[str]):
    from typesafe_sdk import Choice

    questions = {
        "recipient": Choice(
            instructions=(
                "Who is this document addressed to, or whose account or affairs is it about? "
                "Look at the mailing address block, salutation, and account holder names."
            ),
            criteria=dict(config["recipients"]),
        ),
        "topic": Choice(
            instructions="What general category of household paperwork is this document?",
            criteria=dict(config["topics"]),
        ),
    }
    if dates:
        questions["date"] = Choice(
            instructions=(
                "Which of these dates is the date of the document itself: the statement date, letter "
                "date, invoice date, or issue date? Prefer it over transaction dates, due dates, "
                "billing-period boundaries, and dates of birth."
            ),
            criteria={span: None for span in dates} | {NONE: "None of these is the document's own date."},
        )
    if senders:
        questions["sender"] = Choice(
            instructions=(
                "Which of these is the name of the company or organization that sent or issued this "
                "document? When both a company and a person who works there appear, pick the company. "
                "Pick a person only when no organization sent it."
            ),
            criteria={span: None for span in senders} | {NONE: "None of these names the sender."},
        )
    return questions


def ranked(probabilities: dict[str, float], key=lambda option: option) -> list[tuple[str, float]]:
    """Sum probabilities per normalized value (e.g. two spellings of one date) and rank them."""
    totals: dict[str, float] = {}
    for option, p in probabilities.items():
        value = key(option)
        totals[value] = totals.get(value, 0.0) + p
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)


def token(answer, threshold: float, key=lambda option: option, fallback: tuple[str, str] | None = None) -> dict:
    """Turn a Choice answer into {value, source, probability, confidence, alternatives, needs_review}."""
    if answer is None:
        value, source = fallback
        return {"value": value, "source": source, "probability": None, "confidence": None,
                "alternatives": [], "needs_review": True}
    ranks = ranked(answer.probabilities, key)
    (value, probability), alternatives = ranks[0], ranks[1:4]
    source = "jev"
    if value == NONE and fallback:
        value, source = fallback
    return {
        "value": value,
        "source": source,
        "probability": round(probability, 3),
        "confidence": round(answer.confidence, 3),
        "alternatives": [{"value": v, "probability": round(p, 3)} for v, p in alternatives if p >= 0.05],
        # Several spellings of one value split probability, so the summed probability is the review signal.
        "needs_review": source != "jev" or probability < threshold,
    }


def classify_file(client, path: str, config: dict, claimed: set[str]) -> dict:
    result = {"file": path, "proposed_name": None, "proposed_path": None, "needs_review": True,
              "tokens": None, "error": None}
    try:
        text = extract(path)
    except Exception as e:  # noqa: BLE001 — report and continue with the rest of the batch
        result["error"] = f"extraction failed: {e}"
        return result

    dates = find_dates(text, set(config.get("ignore_dates", {})))
    senders = find_senders(text)
    state = {"file_name": os.path.basename(path), "document_text": text[:STATE_CHARS]}
    response = client.system_one(state=state, questions=build_questions(config, dates, senders))
    answers = response.answers

    threshold = float(config.get("review_confidence", 0.6))
    tokens = {
        "date": token(answers.get("date"), threshold, key=lambda o: dates.get(o, o),
                      fallback=(file_creation_date(path), "file_created")),
        "recipient": token(answers["recipient"], threshold),
        "sender": token(answers.get("sender"), threshold, key=lambda o: o if o == NONE else sender_token(o),
                        fallback=("Unknown", "not_found")),
        "topic": token(answers["topic"], threshold),
    }
    stem, ext = os.path.splitext(os.path.basename(path))
    base = "_".join(tokens[k]["value"] for k in ("date", "recipient", "sender", "topic"))
    directory = os.path.dirname(os.path.abspath(path))
    name, n = f"{base}{ext}", 1
    while (os.path.exists(os.path.join(directory, name)) and name != os.path.basename(path)) or name.lower() in claimed:
        n += 1
        name = f"{base}_{n}{ext}"
    claimed.add(name.lower())

    result.update(
        proposed_name=name,
        proposed_path=os.path.join(directory, name),
        needs_review=any(t["needs_review"] for t in tokens.values()),
        tokens=tokens,
        model=response.model,
        usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
    )
    return result


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        config = json.load(f)
    for key in ("recipients", "topics"):
        if not isinstance(config.get(key), dict) or not config[key]:
            raise ValueError(f"config '{key}' must be a non-empty object of name -> description")
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--config", required=True, help="path to the user's renamer_config.json")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except (OSError, ValueError) as e:
        print(f"Error: cannot load config {args.config}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        from typesafe_sdk import TypeSafeClient
    except ImportError:
        print("Error: typesafe-sdk is not installed (pip install -r requirements.txt)", file=sys.stderr)
        sys.exit(2)
    if not os.environ.get("TYPESAFE_API_KEY", "").strip():
        print("Error: TYPESAFE_API_KEY is not set (create one at https://console.typesafe.ai/)", file=sys.stderr)
        sys.exit(2)

    results: list[dict] = []
    claimed: set[str] = set()
    with TypeSafeClient(model=config.get("model", "jev-1.13"), timeout=60.0) as client:
        for path in args.files:
            if not os.path.isfile(path):
                results.append({"file": path, "error": "file not found", "needs_review": True})
                continue
            try:
                results.append(classify_file(client, path, config, claimed))
            except Exception as e:  # noqa: BLE001 — API failure on one file shouldn't sink the batch
                results.append({"file": path, "error": f"classification failed: {e}", "needs_review": True})

    json.dump({"model": config.get("model", "jev-1.13"), "results": results}, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
