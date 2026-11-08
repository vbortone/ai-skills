---
name: renaming-file-personal-style
description: Rename household documents into a standardized `{Date}_{Recipient}_{Sender}_{Topic}` file naming format, using TypeSafe's Jev model to classify each document's date, recipient, sender, and topic. Use when the user asks to rename files, documents, or organize household paperwork.
---

# Household File Renamer

Rename files into the standardized format:

```
{Date}_{Recipient}_{Sender}_{Topic}.{ext}
```

**Example:** `2025-03-15_Alex_Chase-Bank_Financial.pdf`

**Classification is done by TypeSafe's Jev model, not by you.** For documents with a text
layer, `classify.py` finds candidate dates and sender names in code and asks Jev to pick among
them. Photos and scans go to Jev as an image of the first page, and Jev reads them directly;
there is no local OCR. Jev also picks the recipient and topic from the user's configured lists,
and code normalizes the picks into filename tokens. Your
job is to run the script, show the proposals, surface anything Jev was unsure about, and carry
out the renames the user approves. Do not read the documents and substitute your own token
choices. When a token is flagged for review, show Jev's alternatives and let the user decide.

---

## Prerequisites — Check on First Run

Before classifying, verify dependencies are installed. Run this check:

```bash
python -c "import pymupdf; import docx; import typesafe_sdk"
```

If it fails, install Python packages:

```bash
pip install -r "<SKILL_DIR>/requirements.txt"
```

Where `<SKILL_DIR>` is the directory containing this skill (alongside `extract_text.py`).

No system packages are needed. There is no local OCR (no Tesseract, no Poppler): scans and
photos are rendered with PyMuPDF and read by Jev, so the skill runs anywhere pip does.

**TypeSafe API key:** `classify.py` calls the TypeSafe API and needs `TYPESAFE_API_KEY` set in
the environment. If it is missing, the script exits with code 2. Ask the user to create a key at
https://console.typesafe.ai/ and set it. Never ask them to paste the key into the chat.

**Classifier config (`renamer_config.json`):** the user's recipients, topics, and
ignored biographical dates live in a config file in **their** working folder, never in this
skill folder. If they don't have one yet, copy `<SKILL_DIR>/examples/renamer_config.json` to
their working folder and replace the placeholder entries (the `Alex` / `Sam` / `Household`
example household) with the user's own people, nicknames, and dates to ignore, asking the user
for each. Fields:

| Field | Meaning |
|-------|---------|
| `recipients` | Recipient token → description Jev reads (names, nicknames, aliases). Keep an `Unknown` entry. |
| `topics` | Topic token → description. Keep an `Other` entry. |
| `ignore_dates` | ISO date → note. Never used as a document date, in text or image mode. |
| `known_senders` | Sender names Jev may pick for photos and scans (optional). Jev picks answers rather than writing them, so for an image it can only choose a sender from this list plus the senders found by `--sender-history`. |
| `model` | TypeSafe model id (default `jev-latest`). |
| `review_confidence` | A token whose probability is below this is flagged `needs_review` (default `0.6`). |

---

## Workflow

### Step 1: Validate

Confirm each file path exists using the Bash tool (`ls "<path>"`). Report any missing files and continue with the rest.

### Step 2: Classify with Jev

Run the classifier once over all the files:

```bash
python "<SKILL_DIR>/classify.py" --config "<working_folder>/renamer_config.json" \
    --sender-history "<folder of already-renamed files>" "<file_1>" "<file_2>" ...
```

Pass `--sender-history` (repeatable) pointing at where the user keeps already-renamed paperwork;
the senders in those names become the choices Jev has for photos and scans. Ask the user once
where that is if you don't know.

Each file is read one of two ways, then sent to Jev in one request:

- **Text mode** (PDFs with a text layer, DOCX, plain text): `extract_text.py` reads the text.
- **Image mode** (JPG/PNG/TIFF/etc. photos, and PDFs without a text layer): the first page is
  rendered to a JPEG and Jev reads it. The date comes back as year, month, and day picks. A
  sender not in the known list comes back `Unknown` with `source: not_found`; ask the user for it.

It prints one JSON object:

- `results[].proposed_name` / `proposed_path`: the full new name, with a `_2`, `_3` suffix
  already added if the name is taken on disk or earlier in the batch.
- `results[].tokens.{date,recipient,sender,topic}`: each has `value`, `source`
  (`jev`, `file_created` for the date fallback, or `not_found` when no sender candidate fit),
  `probability`, `confidence`, `alternatives` (Jev's runner-up values), and `needs_review`.
- `results[].mode`: `text` or `image`.
- `results[].needs_review`: true if any token was flagged.
- `results[].error`: set when extraction or the API call failed for that file. The rest of the batch still runs.

To debug a single file, run `python "<SKILL_DIR>/extract_text.py" "<file_path>"` for its text
layer, or add `--render out.jpg` to see the image Jev would read.

### Step 3: Confirm with User

Present a table of proposed renames. Mark flagged tokens and list Jev's alternatives for them:

| # | Original File | Proposed Name | Review |
|---|---------------|---------------|--------|
| 1 | statement.pdf | 2025-03-15_Alex_Chase-Bank_Financial.pdf | |
| 2 | letter.docx   | 2025-01-20_Household_IRS_Taxes.docx | sender 0.48 (alt: US-Treasury 0.41) |
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
uses come from the user's `renamer_config.json`. The recipient and ignored-date values below are
placeholders that show the shape; the user's real values live only in their config. When a rule changes, update the config (and `classify.py` for date and sender
handling) rather than overriding Jev's picks by hand.

### 1. Date (`YYYY-MM-DD`)

Code finds every date-shaped span (ISO, `MM/DD/YYYY`, `MM/DD/YY`, `March 15, 2025`, `15 March 2025`)
and Jev picks the document's own date (statement date, letter date, invoice date, etc.).

Dates listed in the config's `ignore_dates` (birthdays, anniversaries) are dropped in code, in
any written form, so they are never offered to Jev as a document date. If the user names another
biographical date, add it to their config.

If no date can be determined from the content, the file creation date is used (`source: "file_created"`).

### 2. Recipient

Determine who the document is addressed to or pertains to. Jev picks exactly one of the config's
`recipients` tokens. With the placeholder config:

| Value | Use when the document is for... |
|-------|-------------------------------|
| `Alex` | Alex Example (also: Al, A. Example, Mr. Example when context implies Alex) |
| `Sam` | Sam Example (also: Samantha Example, Mrs. Example, Ms. Example) |
| `Household` | Both Alex and Sam, "The Example Family", or the household generally |
| `Unknown` | Anyone else, or when the recipient cannot be determined |

Add one token per person or family group the user files paperwork for (relatives, a parent whose
affairs they manage, and so on). Keep the `Unknown` entry.

### 3. Sender

The company or person who sent the document. In text mode, code proposes candidates (capitalized
name phrases from the letterhead and footer, plus web and email domains), Jev picks one, and code
normalizes it into the rules below. In image mode, Jev picks from the known senders
(`known_senders` plus `--sender-history`), already in filename form.

- **Company name takes priority** over an individual person's name when both appear.
- **Replace spaces with dashes** (e.g., "Bank of America" → `Bank-of-America`).
- Trailing corporate suffixes ("Inc.", "LLC", "Corp.", "N.A.", and similar) are removed.
- All-caps letterheads are title-cased; short acronyms stay as written (e.g., `IRS`, `USPS`, `CVS`).
- If the sender cannot be determined, use `Unknown`.

### 4. Topic

Jev picks exactly one of the config's `topics` tokens; each token's description is what Jev reads.
The starter list (`Financial`, `Taxes`, `Insurance`, `Health`, `Utility`, `Other`, and so on)
lives in `<SKILL_DIR>/examples/renamer_config.json`, and the user's own list in their config is
the one that applies.

- To add a topic, add it to the config's `topics` (use dashes instead of spaces for multi-word topics). Keep the `Other` entry.
- When the user supplies a topic by hand (an `error` result, or an edited name), use one of their configured tokens.

### 5. Extension

Keep the original file extension exactly as-is (case-sensitive).

---

## Error Handling

- If Python dependencies are missing, install them automatically (see Prerequisites).
- Never install or run local OCR (Tesseract, etc.) for scans or photos; `classify.py` sends them to Jev as images.
- If `TYPESAFE_API_KEY` is not set or `typesafe-sdk` is missing, `classify.py` exits with code 2. Fix the prerequisite; don't fall back to classifying the documents yourself.
- If a file cannot be read or extracted, or its Jev request fails, `classify.py` reports it in `results[].error`. Report the error and ask the user for the tokens or skip the file.
- If the new filename already exists, append `_2`, `_3`, etc. before the extension.
- Always preserve the original file extension.
