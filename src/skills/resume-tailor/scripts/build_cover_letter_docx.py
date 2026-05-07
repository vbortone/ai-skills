"""
Build an ATS-safe cover letter DOCX from a JSON description.

Usage
-----
    python build_cover_letter_docx.py --input cover.json --output CoverLetter.docx

Or pipe JSON via stdin:
    cat cover.json | python build_cover_letter_docx.py --output CoverLetter.docx

JSON schema
-----------
{
  "name": "Vincent Bortone",
  "contact": {
    "address": "8349 NW 7th Pl, Plantation, FL 33317",
    "phone": "561-343-0765",
    "email": "vbortone@gmail.com",
    "linkedin": "linkedin.com/in/vincentbortone"
  },
  "date": "May 6, 2026",
  "recipient": {
    "name": "Hiring Manager",
    "title": "",
    "company": "Acme Corp",
    "address": ""
  },
  "salutation": "Dear Hiring Manager,",
  "paragraphs": [
    "Opening paragraph...",
    "Experience paragraph...",
    "Differentiator paragraph...",
    "Closing paragraph..."
  ],
  "signoff": "Sincerely,"
}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


BODY_FONT = "Calibri"
BODY_SIZE = Pt(11)
NAME_SIZE = Pt(16)

# ATS safety: Unicode dashes (en-dash U+2013, em-dash U+2014) render as
# garbage in some ATS parsers. Defensive substitution before any text hits
# the document.
_DASH_NORMALIZE = str.maketrans({"–": "-", "—": "-"})


def _ats_safe(text):
    if text is None:
        return text
    if isinstance(text, str):
        return text.translate(_DASH_NORMALIZE)
    return text


def _normalize_strings(obj):
    if isinstance(obj, str):
        return _ats_safe(obj)
    if isinstance(obj, list):
        return [_normalize_strings(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _normalize_strings(v) for k, v in obj.items()}
    return obj


def _set_run_font(run, size=BODY_SIZE, bold=False, italic=False):
    run.font.name = BODY_FONT
    run.font.size = size
    run.font.bold = bold
    run.font.italic = italic
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), BODY_FONT)
    rFonts.set(qn("w:hAnsi"), BODY_FONT)


def _set_paragraph_spacing(paragraph, before=0, after=8, line_spacing=1.15):
    pf = paragraph.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line_spacing


def _add_line(doc, text, *, bold=False, italic=False, size=BODY_SIZE, before=0, after=0, line_spacing=1.15):
    p = doc.add_paragraph()
    _set_paragraph_spacing(p, before=before, after=after, line_spacing=line_spacing)
    if text:
        run = p.add_run(text)
        _set_run_font(run, size=size, bold=bold, italic=italic)
    return p


def build_cover_letter(data: dict, output_path: Path) -> Path:
    data = _normalize_strings(data)
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    style = doc.styles["Normal"]
    style.font.name = BODY_FONT
    style.font.size = BODY_SIZE

    # Letterhead — name + contact
    _add_line(doc, data["name"], bold=True, size=NAME_SIZE, after=0)
    contact = data.get("contact", {})
    contact_parts = [
        contact.get("address", ""),
        contact.get("phone", ""),
        contact.get("email", ""),
        contact.get("linkedin", ""),
    ]
    contact_line = " · ".join([p for p in contact_parts if p])
    _add_line(doc, contact_line, size=Pt(10), after=12)

    # Date
    if data.get("date"):
        _add_line(doc, data["date"], after=12)

    # Recipient
    recipient = data.get("recipient", {})
    if recipient:
        if recipient.get("name"):
            _add_line(doc, recipient["name"], after=0)
        if recipient.get("title"):
            _add_line(doc, recipient["title"], after=0)
        if recipient.get("company"):
            _add_line(doc, recipient["company"], after=0)
        if recipient.get("address"):
            _add_line(doc, recipient["address"], after=0)
        # spacer
        _add_line(doc, "", after=8)

    # Salutation
    _add_line(doc, data.get("salutation", "Dear Hiring Manager,"), after=10)

    # Body paragraphs
    for para in data.get("paragraphs", []):
        _add_line(doc, para, after=10, line_spacing=1.15)

    # Signoff
    _add_line(doc, data.get("signoff", "Sincerely,"), before=4, after=24)
    _add_line(doc, data["name"], after=0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--input", "-i", help="Path to JSON. If omitted, reads stdin.")
    parser.add_argument("--output", "-o", required=True, help="Output DOCX path.")
    args = parser.parse_args(argv)

    if args.input:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        data = json.loads(sys.stdin.read())

    out = build_cover_letter(data, Path(args.output))
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
