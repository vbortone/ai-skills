---
name: renaming-file-personal-style
description: Rename documents into the standardized Bortone family file naming format, using TypeSafe's Jev model to classify each document's date, recipient, sender, and topic. Use when the user asks to rename files, documents, or organize household paperwork.
---

# Bortone File Renamer

Rename files into the standardized format:

```
{Date}_{Recipient}_{Sender}_{Topic}.{ext}
```

**Example:** `2025-03-15_Vincent_Chase-Bank_Financial.pdf`

**Classification is done by TypeSafe's Jev model, not by you.** `classify.py` finds candidate
dates and sender names in code, asks Jev to pick among them (and to pick the recipient and
topic from the user's configured lists), then normalizes the picks into filename tokens. Your
job is to run the script, show the proposals, surface anything Jev was unsure about, and carry
out the renames the user approves. Do not read the documents and substitute your own token
choices. When a token is flagged for review, show Jev's alternatives and let the user decide.

---

## Prerequisites — Check on First Run

Before extracting text, verify dependencies are installed. Run this check:

```bash
python -c "import fitz; import docx; import pdfplumber; import pytesseract; from PIL import Image; from pdf2image import convert_from_path; import typesafe_sdk"
```

If it fails, install Python packages:

```bash
pip install -r "<SKILL_DIR>/requirements.txt"
```

Where `<SKILL_DIR>` is the directory containing this skill (alongside `extract_text.py`).

**External dependencies** (needed for OCR of images and scanned PDFs):

- **Tesseract OCR**: The `pytesseract` package requires the Tesseract engine.
  - macOS: `brew install tesseract`
  - Linux (Debian/Ubuntu): `sudo apt-get install tesseract-ocr`
  - Windows: `choco install tesseract` or download from the UB Mannheim Tesseract GitHub releases page and add to PATH.
- **Poppler**: The `pdf2image` package requires Poppler utilities.
  - macOS: `brew install poppler`
  - Linux (Debian/Ubuntu): `sudo apt-get install poppler-utils`
  - Windows: `choco install poppler` or download binaries and add to PATH.

If the user only needs to process text-based PDFs and DOCX files, Tesseract and Poppler are not required.

**TypeSafe API key:** `classify.py` calls the TypeSafe API and needs `TYPESAFE_API_KEY` set in
the environment. If it is missing, the script exits with code 2. Ask the user to create a key at
https://console.typesafe.ai/ and set it. Never ask them to paste the key into the chat.

**Classifier config (`renamer_config.json`):** the user's recipients, topics, and
ignored biographical dates live in a config file in **their** working folder, never in this
skill folder. If they don't have one yet, copy `<SKILL_DIR>/examples/renamer_config.json` to
their working folder and replace the placeholder entries with the values from the Token Rules
below, confirming with the user. Fields:

| Field | Meaning |
|-------|---------|
| `recipients` | Recipient token → description Jev reads (names, nicknames, aliases). Keep an `Unknown` entry. |
| `topics` | Topic token → description. Keep an `Other` entry. |
| `ignore_dates` | ISO date → note. These are dropped before Jev sees the date candidates. |
| `model` | TypeSafe model id (default `jev-latest`). |
| `review_confidence` | A token whose probability is below this is flagged `needs_review` (default `0.6`). |

---

## Workflow

### Step 1: Validate

Confirm each file path exists using the Bash tool (`ls "<path>"`). Report any missing files and continue with the rest.

### Step 2: Classify with Jev

Run the classifier once over all the files:

```bash
python "<SKILL_DIR>/classify.py" --config "<working_folder>/renamer_config.json" "<file_1>" "<file_2>" ...
```

It extracts text (via `extract_text.py`: PDFs including scanned ones, DOCX, images by OCR,
plain text), sends one Jev request per file, and prints one JSON object:

- `results[].proposed_name` / `proposed_path`: the full new name, with a `_2`, `_3` suffix
  already added if the name is taken on disk or earlier in the batch.
- `results[].tokens.{date,recipient,sender,topic}`: each has `value`, `source`
  (`jev`, `file_created` for the date fallback, or `not_found` when no sender candidate fit),
  `probability`, `confidence`, `alternatives` (Jev's runner-up values), and `needs_review`.
- `results[].needs_review`: true if any token was flagged.
- `results[].error`: set when extraction or the API call failed for that file. The rest of the batch still runs.

To debug a single file's extracted text, run `python "<SKILL_DIR>/extract_text.py" "<file_path>"`.

### Step 3: Confirm with User

Present a table of proposed renames. Mark flagged tokens and list Jev's alternatives for them:

| # | Original File | Proposed Name | Review |
|---|---------------|---------------|--------|
| 1 | statement.pdf | 2025-03-15_Vincent_Chase-Bank_Financial.pdf | |
| 2 | letter.docx   | 2025-01-20_Bortone_IRS_Taxes.docx | sender 0.48 (alt: US-Treasury 0.41) |
| 3 | scan.jpg      | 2024-11-02_Unknown_Unknown_Other.jpg | date from file creation; no sender found |

For files with an `error`, report the error and ask the user for the tokens (or skip the file).
Ask the user to confirm, or let them adjust individual entries before proceeding.

### Step 4: Rename

Execute the rename using the Bash tool:

```bash
mv "<original_path>" "<proposed_path>"
```

If the user edited a name, check that the target doesn't already exist before moving. If it does, append `_2`, `_3`, etc. before the extension.

### Step 5: Report

Confirm which files were renamed successfully and report any errors.

---

## Token Rules

These rules define the four tokens. `classify.py` applies them: the date, sender, and topic
questions it sends Jev encode this guidance, and the recipient, topic, and ignored-date lists it
uses come from the user's `renamer_config.json`. The tables below are the values that config
should hold. When a rule changes, update the config (and `classify.py` for date and sender
handling) rather than overriding Jev's picks by hand.

### 1. Date (`YYYY-MM-DD`)

Code finds every date-shaped span (ISO, `MM/DD/YYYY`, `MM/DD/YY`, `March 15, 2025`, `15 March 2025`)
and Jev picks the document's own date (statement date, letter date, invoice date, etc.).

**IGNORE these known biographical dates** — they are not document dates:
- **1974-01-31** — Vincent Bortone's birthday (also: "January 31, 1974", "01/31/1974", etc.)
- **1972-04-14** — Jennifer Bortone's birthday (also: "April 14, 1972", "04/14/1972", etc.)
- **2012-10-20** — Vincent and Jennifer's wedding date (also: "October 20, 2012", "10/20/2012", etc.)

If multiple valid dates exist, prefer the document/statement/letter date over transaction dates or due dates.

If no date can be determined from the content, the file creation date is used (`source: "file_created"`).

### 2. Recipient

Determine who the document is addressed to or pertains to. Use exactly one of these values:

| Value | Use when the document is for... |
|-------|-------------------------------|
| `Vincent` | Vincent Bortone (also: Vince, Vincent M. Bortone, Mr. Bortone when context implies Vincent) |
| `Jennifer` | Jennifer Bortone (also: Jen, Jennifer A. Bortone, Mrs. Bortone, Ms. Bortone) |
| `Bortone` | Both Vincent and Jennifer, "The Bortones", "Bortone Family", or the household generally |
| `Margaret` | Margaret Bortone (also: Peggy Bortone) |
| `Strollo` | Richard Strollo or Vivian Strollo |
| `Mel` | Camille Crifasi (also: Mel Crifasi, Aunt Mel) |
| `MaryAnn` | Maryann Devitt (also: Aunt Maryann) |
| `Coslett` | Bob Coslett or Peggy Coslett (also: Aunt Peggy, Uncle Bob) |
| `Unknown` | Anyone else, or when the recipient cannot be determined |

### 3. Sender

The company or person who sent the document. Code proposes candidates (capitalized name phrases
from the letterhead and footer, plus web and email domains), Jev picks one, and code normalizes it
into the rules below.

- **Company name takes priority** over an individual person's name when both appear.
- **Replace spaces with dashes** (e.g., "Bank of America" → `Bank-of-America`).
- Remove trailing corporate suffixes like "Inc.", "LLC", "Corp." unless they are essential to identify the sender.
- Common abbreviations are acceptable (e.g., `IRS`, `US-Treasury`, `USPS`).
- If the sender cannot be determined, use `Unknown`.

### 4. Topic

Choose the most fitting general topic for the document:

| Topic | Description |
|-------|-------------|
| `Financial` | Bank statements, account notices, general financial documents |
| `Taxes` | Tax returns, W-2s, 1099s, IRS correspondence |
| `Insurance` | Insurance policies, claims, EOBs (non-health) |
| `CreditCard` | Credit card statements, offers, notices |
| `Health` | Medical bills, health insurance EOBs, lab results, prescriptions |
| `Home` | Mortgage, property tax, home repairs, HOA |
| `Auto` | Car insurance, registration, repairs, DMV |
| `Ad` | Advertisements, promotional mailers, marketing |
| `Legal` | Legal notices, contracts, court documents |
| `Employment` | Pay stubs, offer letters, HR documents |
| `Retirement` | 401k, IRA, pension, Social Security |
| `Investment` | Brokerage statements, stock/fund correspondence |
| `Utility` | Electric, gas, water, phone, internet bills |
| `Dining` | Restaurant receipts, food delivery, cafe charges |
| `Bar` | Bar tabs, nightlife, alcohol-related receipts |
| `Travel` | Flights, hotels, rental cars, vacation bookings, transportation |
| `Shopping` | Retail purchases, online orders, general merchandise receipts |
| `Other` | Anything that does not fit the above categories |

- Jev can only choose a configured topic. To add one, add it to the config's `topics` (use dashes instead of spaces for multi-word topics).
- If the document is too complicated to determine its topic, use `Other`.

### 5. Extension

Keep the original file extension exactly as-is (case-sensitive).

---

## Error Handling

- If Python dependencies are missing, install them automatically (see Prerequisites).
- If Tesseract or Poppler are missing and needed, inform the user and provide installation instructions.
- If `TYPESAFE_API_KEY` is not set or `typesafe-sdk` is missing, `classify.py` exits with code 2. Fix the prerequisite; don't fall back to classifying the documents yourself.
- If a file cannot be read or extracted, or its Jev request fails, `classify.py` reports it in `results[].error`. Report the error and ask the user for the tokens or skip the file.
- If the new filename already exists, append `_2`, `_3`, etc. before the extension.
- Always preserve the original file extension.
