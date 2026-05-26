"""
Build an ATS-safe resume DOCX from a JSON description.

Usage
-----
    python build_resume_docx.py --input resume.json --output Resume.docx

Or pipe JSON via stdin:
    cat resume.json | python build_resume_docx.py --output Resume.docx

JSON schema
-----------
{
  "name": "Jane Doe",
  "headline": "Director of Engineering",
  "contact": {
    "address": "City, State",
    "phone": "555-555-5555",
    "email": "jane@example.com",
    "linkedin": "linkedin.com/in/janedoe"
  },
  "summary": "Three to four sentence summary tailored to the target role.",
  "experience": [
    {
      "company": "Current Employer",
      "title": "Senior Title",
      "dates": "08/2018 – Present",
      "location": "City, State",
      "context": "Optional one-line description of the engagement.",
      "bullets": [
        "Quantified achievement that maps to the JD ...",
        "Another quantified achievement ..."
      ]
    }
  ],
  "education": [
    {
      "degree": "Master of Science in Field",
      "school": "University Name",
      "location": "City, State",
      "dates": "08/2023 – 05/2025",
      "details": "GPA: 3.9"
    }
  ],
  "skills": [
    {"group": "Cloud & Infrastructure", "items": ["Azure", "AKS", "Docker"]},
    {"group": "Languages", "items": ["C#", ".NET", "Python"]}
  ],
  "certifications": [
    {"name": "Microsoft Certified: Azure Fundamentals", "issuer": "Microsoft", "dates": "05/2023 – Present"}
  ]
}

Design notes
------------
This script intentionally does not use tables for layout, text boxes,
or images — those break ATS parsers. Dates are right-aligned via a
right tab stop instead of a two-column table.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_output import (  # noqa: E402
    build_report,
    find_config,
    load_config,
    verify_anonymization,
    verify_page_count,
)


RESUME_MAX_PAGES = 2


BODY_FONT = "Calibri"
BODY_SIZE = Pt(11)
NAME_SIZE = Pt(20)
HEADLINE_SIZE = Pt(12)
SECTION_SIZE = Pt(13)
ROLE_SIZE = Pt(11)
HEADING_RULE_COLOR = RGBColor(0x40, 0x40, 0x40)

# ATS safety: Unicode dashes (en-dash U+2013, em-dash U+2014) render as
# garbage in some ATS parsers. Defensive substitution before any text hits
# the document so the JSON layer can't accidentally introduce them.
_DASH_NORMALIZE = str.maketrans({"–": "-", "—": "-"})


def _ats_safe(text):
    if text is None:
        return text
    if isinstance(text, str):
        return text.translate(_DASH_NORMALIZE)
    return text


def _normalize_strings(obj):
    """Recursively normalize ATS-unsafe characters in every string value."""
    if isinstance(obj, str):
        return _ats_safe(obj)
    if isinstance(obj, list):
        return [_normalize_strings(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _normalize_strings(v) for k, v in obj.items()}
    return obj


def _set_run_font(run, size=BODY_SIZE, bold=False, italic=False, color=None):
    run.font.name = BODY_FONT
    run.font.size = size
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    # Force Calibri for East Asian fallback so Word doesn't substitute
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), BODY_FONT)
    rFonts.set(qn("w:hAnsi"), BODY_FONT)
    rFonts.set(qn("w:cs"), BODY_FONT)


def _set_paragraph_spacing(paragraph, before=0, after=0, line_spacing=1.0):
    pf = paragraph.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line_spacing


def _add_horizontal_rule(paragraph):
    """Add a thin bottom border to the paragraph as a section divider."""
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")  # 0.75 pt
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "404040")
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_right_tab(paragraph, position_inches=7.0):
    """Add a right-aligned tab stop near the right margin for date alignment."""
    pf = paragraph.paragraph_format
    pf.tab_stops.add_tab_stop(Inches(position_inches), WD_TAB_ALIGNMENT.RIGHT)


def _add_contact_line(doc, contact):
    parts = []
    if contact.get("address"):
        parts.append(contact["address"])
    if contact.get("phone"):
        parts.append(contact["phone"])
    if contact.get("email"):
        parts.append(contact["email"])
    if contact.get("linkedin"):
        parts.append(contact["linkedin"])
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_paragraph_spacing(p, before=0, after=2)
    run = p.add_run(" · ".join(parts))
    _set_run_font(run, size=Pt(10))


def _add_section_heading(doc, text):
    p = doc.add_paragraph()
    _set_paragraph_spacing(p, before=8, after=2)
    run = p.add_run(text.upper())
    _set_run_font(run, size=SECTION_SIZE, bold=True)
    _add_horizontal_rule(p)


def _add_role_header(doc, company, title, dates, location):
    """First line: bold company  ........  right-aligned dates.
    Second line: italic title  .......  right-aligned location."""
    # Line 1
    p1 = doc.add_paragraph()
    _set_paragraph_spacing(p1, before=4, after=0)
    _add_right_tab(p1)
    r_company = p1.add_run(company)
    _set_run_font(r_company, size=ROLE_SIZE, bold=True)
    p1.add_run("\t")
    r_dates = p1.add_run(dates)
    _set_run_font(r_dates, size=ROLE_SIZE, bold=True)

    # Line 2
    p2 = doc.add_paragraph()
    _set_paragraph_spacing(p2, before=0, after=2)
    _add_right_tab(p2)
    r_title = p2.add_run(title)
    _set_run_font(r_title, size=ROLE_SIZE, italic=True)
    p2.add_run("\t")
    r_loc = p2.add_run(location or "")
    _set_run_font(r_loc, size=ROLE_SIZE, italic=True)


def _add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    _set_paragraph_spacing(p, before=0, after=2, line_spacing=1.15)
    pf = p.paragraph_format
    pf.left_indent = Inches(0.25)
    # Set the bullet's run font (List Bullet style might use a different default)
    for run in p.runs:
        _set_run_font(run, size=BODY_SIZE)
    run = p.add_run(text)
    _set_run_font(run, size=BODY_SIZE)


def _add_paragraph(doc, text, italic=False, before=0, after=2):
    p = doc.add_paragraph()
    _set_paragraph_spacing(p, before=before, after=after, line_spacing=1.15)
    run = p.add_run(text)
    _set_run_font(run, size=BODY_SIZE, italic=italic)
    return p


def build_resume(data: dict, output_path: Path) -> Path:
    data = _normalize_strings(data)
    doc = Document()

    # Margins — keep generous but not wasteful
    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)

    # Set default style font
    style = doc.styles["Normal"]
    style.font.name = BODY_FONT
    style.font.size = BODY_SIZE

    # Header — name + headline + contact (NOT in document header element)
    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_paragraph_spacing(p_name, before=0, after=0)
    r_name = p_name.add_run(data["name"])
    _set_run_font(r_name, size=NAME_SIZE, bold=True)

    if data.get("headline"):
        p_headline = doc.add_paragraph()
        p_headline.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_paragraph_spacing(p_headline, before=0, after=0)
        r_headline = p_headline.add_run(data["headline"])
        _set_run_font(r_headline, size=HEADLINE_SIZE, italic=True)

    _add_contact_line(doc, data.get("contact", {}))

    # Summary
    if data.get("summary"):
        _add_section_heading(doc, "Summary")
        _add_paragraph(doc, data["summary"], before=2, after=4)

    # Experience
    if data.get("experience"):
        _add_section_heading(doc, "Experience")
        for role in data["experience"]:
            _add_role_header(
                doc,
                company=role.get("company", ""),
                title=role.get("title", ""),
                dates=role.get("dates", ""),
                location=role.get("location", ""),
            )
            if role.get("context"):
                _add_paragraph(doc, role["context"], italic=True, before=0, after=2)
            for bullet in role.get("bullets", []):
                _add_bullet(doc, bullet)

    # Education
    if data.get("education"):
        _add_section_heading(doc, "Education")
        for edu in data["education"]:
            p = doc.add_paragraph()
            _set_paragraph_spacing(p, before=2, after=0)
            _add_right_tab(p)
            r_degree = p.add_run(edu.get("degree", ""))
            _set_run_font(r_degree, size=ROLE_SIZE, bold=True)
            p.add_run("\t")
            r_dates = p.add_run(edu.get("dates", ""))
            _set_run_font(r_dates, size=ROLE_SIZE, bold=True)

            sub = doc.add_paragraph()
            _set_paragraph_spacing(sub, before=0, after=2)
            _add_right_tab(sub)
            r_school = sub.add_run(edu.get("school", ""))
            _set_run_font(r_school, size=ROLE_SIZE, italic=True)
            sub.add_run("\t")
            r_loc = sub.add_run(edu.get("location", ""))
            _set_run_font(r_loc, size=ROLE_SIZE, italic=True)

            if edu.get("details"):
                _add_paragraph(doc, edu["details"], before=0, after=2)

    # Skills
    if data.get("skills"):
        _add_section_heading(doc, "Skills")
        for group in data["skills"]:
            p = doc.add_paragraph()
            _set_paragraph_spacing(p, before=2, after=0, line_spacing=1.15)
            r_group = p.add_run(f"{group.get('group', '')}: ")
            _set_run_font(r_group, size=BODY_SIZE, bold=True)
            r_items = p.add_run(", ".join(group.get("items", [])))
            _set_run_font(r_items, size=BODY_SIZE)

    # Certifications
    if data.get("certifications"):
        _add_section_heading(doc, "Certifications")
        for cert in data["certifications"]:
            p = doc.add_paragraph()
            _set_paragraph_spacing(p, before=2, after=0)
            _add_right_tab(p)
            label = cert.get("name", "")
            issuer = cert.get("issuer", "")
            if issuer:
                label = f"{label} - {issuer}"
            r_name = p.add_run(label)
            _set_run_font(r_name, size=BODY_SIZE, bold=True)
            if cert.get("dates"):
                p.add_run("\t")
                r_dates = p.add_run(cert["dates"])
                _set_run_font(r_dates, size=BODY_SIZE)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--input", "-i", help="Path to resume JSON. If omitted, reads stdin.")
    parser.add_argument("--output", "-o", required=True, help="Output DOCX path.")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help=(
            "Path to tailor_config.json. If omitted, walks up from the output "
            "directory looking for the file."
        ),
    )
    parser.add_argument(
        "--skip-anonymization",
        action="store_true",
        help=(
            "Skip the anonymization check (use when the target JD employer matches "
            "one of your configured anonymization patterns)."
        ),
    )
    parser.add_argument(
        "--no-strict-pages",
        action="store_true",
        help="Warn but don't fail on page-count overage. Default cap is 2 pages.",
    )
    parser.add_argument(
        "--skip-page-check",
        action="store_true",
        help="Skip the page-count check entirely (e.g. when MS Word isn't available).",
    )
    args = parser.parse_args(argv)

    if args.input:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    else:
        data = json.loads(sys.stdin.read())

    out = build_resume(data, Path(args.output))

    config_path = args.config or find_config([out.parent, Path.cwd()])
    config = load_config(config_path)

    violations = verify_anonymization(out, config=config, skip=args.skip_anonymization)
    page_count: int | None = None
    if not args.skip_page_check:
        page_count = verify_page_count(out, max_pages=RESUME_MAX_PAGES)

    report = build_report(
        out,
        violations,
        page_count,
        RESUME_MAX_PAGES if not args.skip_page_check else None,
        config_path,
    )
    exit_code = 0

    if violations:
        exit_code |= 1
        print(
            f"\nERROR: rendered resume {out.name} contains "
            f"{len(violations)} anonymization violation(s):",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  - {v.token!r} matched {v.match!r} near: {v.context!r}", file=sys.stderr)
        print(
            "\nFix the resume JSON to use anonymized framing per your master_profile.md, "
            "then re-run. Pass --skip-anonymization only when the target JD employer matches "
            "one of your configured anonymization patterns.",
            file=sys.stderr,
        )

    if report["page_over_cap"]:
        level = "WARN" if args.no_strict_pages else "ERROR"
        print(
            f"\n{level}: rendered resume {out.name} is {page_count} pages "
            f"(cap is {RESUME_MAX_PAGES}).",
            file=sys.stderr,
        )
        if not args.no_strict_pages:
            exit_code |= 2
            print(
                "Trim per your master_profile.md tailoring rules — usually the lowest-impact "
                "legacy-employer bullets first, then older current-employer bullets, then "
                "shorten the longest lines.",
                file=sys.stderr,
            )

    print(json.dumps(report))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
