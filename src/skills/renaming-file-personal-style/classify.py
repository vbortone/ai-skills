#!/usr/bin/env python3
"""
classify.py — Propose {Date}_{Recipient}_{Sender}_{Topic}.{ext} names with TypeSafe's Jev model.

Jev picks answers but does not write them. No local OCR: a file is read one of two ways.

Text mode (PDFs with a text layer, DOCX, plain text): code reads the text and offers candidates.
  * Date      — code finds every date-shaped span and parses it; Jev picks which span is the
                document's own date. Code converts it to YYYY-MM-DD and drops dates listed in
                `ignore_dates`.
  * Sender    — code finds capitalized name phrases and web/email domains; Jev picks the issuing
                organization. Code turns the pick into the dashed filename form.

Image mode (photos, scans, PDFs without a text layer): the first page goes to Jev as an image.
  * Date      — Jev reads the year, month, and day as three choices; code assembles and validates them.
  * Sender    — Jev picks from the user's known senders: `known_senders` in the config plus the senders
                of already-named files under --sender-history. A sender it hasn't seen before comes back
                Unknown and flagged, because Jev chooses answers rather than writing them.

Both modes:
  * Recipient — Jev picks one entry from the config's `recipients` roster.
  * Topic     — Jev picks one entry from the config's `topics` list.
  * Date falls back to the file's creation date when no document date is found.

All questions for a file go to Jev together in one request.

Usage:
    python classify.py --config <renamer_config.json> [--sender-history <dir> ...] <file> [<file> ...]

Requires the TYPESAFE_API_KEY environment variable (https://console.typesafe.ai/).
The config file holds the user's own recipients, topics and ignored dates; see
examples/renamer_config.json for the shape.

Output: one JSON object on stdout:
    {"model": "...", "results": [{"file", "proposed_name", "proposed_path", "needs_review",
                                  "tokens": {"date", "recipient", "sender", "topic"}, "error"}]}
Each result has `mode` ("text" or "image"). Each token carries its `value`, `source`, the
probability Jev gave it, Jev's `confidence`, the runner-up `alternatives`, and `needs_review`.

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
from extract_text import extract, needs_image, render_first_page  # noqa: E402

NONE = "none"
MAX_OPTIONS = 250  # Choice allows 255 options; leave room for the NONE option
# Images are an experimental API feature; requests carrying one must opt in with this header.
IMAGE_HEADERS = {"TypeSafe-Danger-Zone-Images": "true"}
FIRST_YEAR = 1990  # earliest year offered when Jev reads a date off an image
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
    # 15 March 2025 / 24th March 2026
    (re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_RE})\.?,?\s+(\d{{4}})\b", re.I), ("d", "mon", "y")),
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


def build_image_questions(config: dict, senders: dict[str, str]):
    """Questions for a page image: the date as year/month/day choices, the sender from known senders."""
    from typesafe_sdk import Choice

    questions = build_questions(config, {}, [])
    doc_date = "the document's own date (statement, letter, invoice, receipt, or issue date)"
    no_date = {NONE: "No document date is visible."}
    questions["date_year"] = Choice(
        instructions=f"What is the year of {doc_date}? Not a due date, transaction date, or date of birth.",
        criteria={str(y): None for y in range(dt.date.today().year + 1, FIRST_YEAR - 1, -1)} | no_date)
    questions["date_month"] = Choice(
        instructions=f"What is the month of {doc_date}?",
        criteria={f"{m:02d}": dt.date(2000, m, 1).strftime("%B") for m in range(1, 13)} | no_date)
    questions["date_day"] = Choice(
        instructions=f"What is the day of the month of {doc_date}?",
        criteria={f"{d:02d}": None for d in range(1, 32)} | no_date)
    if senders:
        questions["sender"] = Choice(
            instructions=(
                "Which of these is the company or organization that sent or issued this document? "
                "Pick a person only when no organization sent it."
            ),
            criteria={label: None for label in senders} | {NONE: "None of these; the sender is not in this list."},
        )
    return questions


SENDER_FROM_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[^_]+_([^_]+)_[^_.]+(?:_\d+)?\.\w+$")


def known_senders(config: dict, history_dirs: list[str]) -> dict[str, str]:
    """{option label: filename token} from config `known_senders` and already-named files, most used first."""
    counts: dict[str, int] = {}
    for name in config.get("known_senders", []):
        tok = sender_token(name)
        counts[tok] = counts.get(tok, 0) + 1_000_000  # configured senders always make the cut
    for directory in history_dirs:
        for _, _, names in os.walk(directory):
            for name in names:
                match = SENDER_FROM_NAME_RE.match(name)
                if match and match.group(1) != "Unknown":
                    counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    tokens = sorted(counts, key=lambda t: (-counts[t], t))[:MAX_OPTIONS]
    return {t.replace("-", " "): t for t in tokens}


def _iso(year: str, month: str, day: str) -> str | None:
    try:
        return dt.date(int(year), int(month), int(day)).isoformat()
    except ValueError:  # "none", or an impossible date such as Feb 30
        return None


def date_token(answers, threshold: float, ignore: set[str], fallback: tuple[str, str]) -> dict:
    """Assemble an image-mode date from Jev's year, month, and day picks."""
    keys = ("date_year", "date_month", "date_day")
    parts = [ranked(answers[k].probabilities) for k in keys]
    picks = [p[0] for p in parts]
    probability = picks[0][1] * picks[1][1] * picks[2][1]
    confidence = min(answers[k].confidence for k in keys)
    alternatives = []
    for i, ranks in enumerate(parts):  # swap in one part's runner-up: the likeliest single misreads
        if len(ranks) > 1 and ranks[1][0] != NONE:
            alt_picks = list(picks)
            alt_picks[i] = ranks[1]
            alt = _iso(*(v for v, _ in alt_picks))
            p = alt_picks[0][1] * alt_picks[1][1] * alt_picks[2][1]
            if alt and alt not in ignore and p >= 0.05:
                alternatives.append({"value": alt, "probability": round(p, 3)})
    alternatives = sorted(alternatives, key=lambda a: -a["probability"])[:3]
    iso = _iso(*(v for v, _ in picks))
    value, source = (iso, "jev") if iso and iso not in ignore else fallback
    return {"value": value, "source": source, "probability": round(probability, 3),
            "confidence": round(confidence, 3), "alternatives": alternatives,
            "needs_review": source != "jev" or probability < threshold}


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


def classify_file(client, path: str, config: dict, claimed: set[str],
                  senders_known: dict[str, str] | None = None) -> dict:
    result = {"file": path, "mode": None, "proposed_name": None, "proposed_path": None, "needs_review": True,
              "tokens": None, "error": None}
    ignore = set(config.get("ignore_dates", {}))
    threshold = float(config.get("review_confidence", 0.6))
    date_fallback = (file_creation_date(path), "file_created")
    sender_fallback = ("Unknown", "not_found")
    try:
        text = extract(path)
        image = render_first_page(path) if needs_image(path, text) else None
    except Exception as e:  # noqa: BLE001 — report and continue with the rest of the batch
        result["error"] = f"extraction failed: {e}"
        return result

    if image is None:
        result["mode"] = "text"
        dates = find_dates(text, ignore)
        senders = find_senders(text)
        state = {"file_name": os.path.basename(path), "document_text": text[:STATE_CHARS]}
        response = client.system_one(state=state, questions=build_questions(config, dates, senders))
        answers = response.answers
        date = token(answers.get("date"), threshold, key=lambda o: dates.get(o, o), fallback=date_fallback)
        sender = token(answers.get("sender"), threshold, key=lambda o: o if o == NONE else sender_token(o),
                       fallback=sender_fallback)
    else:
        from typesafe_sdk import Image

        result["mode"] = "image"
        senders = senders_known or {}
        state = {"file_name": os.path.basename(path), "page_image": Image(image)}
        response = client.system_one(state=state, questions=build_image_questions(config, senders))
        answers = response.answers
        date = date_token(answers, threshold, ignore, date_fallback)
        sender = token(answers.get("sender"), threshold, key=lambda o: senders.get(o, o), fallback=sender_fallback)

    tokens = {
        "date": date,
        "recipient": token(answers["recipient"], threshold),
        "sender": sender,
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
    parser.add_argument("--sender-history", action="append", default=[], metavar="DIR",
                        help="folder of already-named files whose senders Jev may pick for images (repeatable)")
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
    senders_known = known_senders(config, args.sender_history)
    with TypeSafeClient(model=config.get("model", "jev-latest"), timeout=60.0, headers=IMAGE_HEADERS) as client:
        for path in args.files:
            if not os.path.isfile(path):
                results.append({"file": path, "error": "file not found", "needs_review": True})
                continue
            try:
                results.append(classify_file(client, path, config, claimed, senders_known))
            except Exception as e:  # noqa: BLE001 — API failure on one file shouldn't sink the batch
                results.append({"file": path, "error": f"classification failed: {e}", "needs_review": True})

    json.dump({"model": config.get("model", "jev-latest"), "results": results}, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
