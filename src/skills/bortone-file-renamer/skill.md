---
name: bortone-file-renamer
description: Rename documents into the standardized Bortone family file naming format based on document content analysis. Use when the user asks to rename files, documents, or organize household paperwork.
---

# Bortone File Renamer

Rename files into the standardized format:

```
{Date}_{Recipient}_{Sender}_{Topic}.{ext}
```

**Example:** `2025-03-15_Vincent_Chase-Bank_Financial.pdf`

---

## Prerequisites — Check on First Run

Before extracting text, verify dependencies are installed. Run this check:

```bash
python -c "import fitz; import docx; import pdfplumber; import pytesseract; from PIL import Image; from pdf2image import convert_from_path"
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

---

## Workflow

For each file the user provides:

### Step 1: Validate

Confirm each file path exists using the Bash tool (`ls "<path>"`). Report any missing files and continue with the rest.

### Step 2: Extract Content

Use the Python extraction script to get text from the document:

```bash
python "<SKILL_DIR>/extract_text.py" "<file_path>"
```

This handles PDFs (text-based and scanned), DOCX, images (OCR), and plain text files.

If extraction fails or returns empty, note the failure and attempt to determine naming tokens from the filename and file metadata alone.

### Step 3: Get File Creation Date (Fallback)

Retrieve the file's creation date in case no date is found in the content:

```bash
python -c "import os, datetime; print(datetime.datetime.fromtimestamp(os.path.getctime(r'<file_path>')).strftime('%Y-%m-%d'))"
```

### Step 4: Analyze Content

Using the extracted text, determine the four naming tokens according to the rules below.

### Step 5: Confirm with User

Present a table of proposed renames:

| # | Original File | Proposed Name |
|---|---------------|---------------|
| 1 | statement.pdf | 2025-03-15_Vincent_Chase-Bank_Financial.pdf |
| 2 | letter.docx   | 2025-01-20_Bortone_IRS_Taxes.docx |

Ask the user to confirm, or let them adjust individual entries before proceeding.

### Step 6: Rename

Execute the rename using the Bash tool:

```bash
mv "<original_path>" "<directory>/<new_name>"
```

If the target filename already exists, append a numeric suffix before the extension (e.g., `_2`, `_3`).

### Step 7: Report

Confirm which files were renamed successfully and report any errors.

---

## Token Rules

### 1. Date (`YYYY-MM-DD`)

Find the most prominent date in the document (statement date, letter date, invoice date, etc.).

**IGNORE these known biographical dates** — they are not document dates:
- **1974-01-31** — Vincent Bortone's birthday (also: "January 31, 1974", "01/31/1974", etc.)
- **1972-04-14** — Jennifer Bortone's birthday (also: "April 14, 1972", "04/14/1972", etc.)
- **2012-10-20** — Vincent and Jennifer's wedding date (also: "October 20, 2012", "10/20/2012", etc.)

If multiple valid dates exist, prefer the document/statement/letter date over transaction dates or due dates.

If no date can be determined from the content, use the file creation date from Step 3.

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

The company or person who sent the document.

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
| `Other` | Anything that does not fit the above categories |

- If you create a topic of more than one word, use dashes instead of spaces.
- If the document is too complicated to determine its topic, use `Other`.

### 5. Extension

Keep the original file extension exactly as-is (case-sensitive).

---

## Error Handling

- If Python dependencies are missing, install them automatically (see Prerequisites).
- If Tesseract or Poppler are missing and needed, inform the user and provide installation instructions.
- If a file cannot be read or extracted, report the error and skip it.
- If the new filename already exists, append `_2`, `_3`, etc. before the extension.
- Always preserve the original file extension.
