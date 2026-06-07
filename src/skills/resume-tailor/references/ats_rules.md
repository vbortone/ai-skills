# ATS-Safe DOCX Rules

Applicant Tracking Systems (ATS) parse resumes with mixed-quality engines (Workday, iCIMS, Greenhouse, Taleo, Lever, etc.). What renders fine in Word can get mangled into garbage by a poor parser. Optimize for the lowest common denominator.

The `build_resume_docx.py` script bakes most of these rules in. This document exists so future iterations of the skill don't drift from the principles.

## Hard rules (never break)

0. **2 pages maximum.** Never spill to page 3. ATS parsers handle 2-page resumes fine; recruiters at director-and-above seniority expect 1-2 pages. A 3rd page reads as undisciplined regardless of content. If the resume overflows, cut bullets per the trim order in `tailoring_playbook.md` "Length decisions". Enforced post-render by `scripts/verify_output.py` (renders to PDF via LibreOffice headless — same on Windows/Linux/macOS — counts pages, fails the build at page_count > 2; skipped, not failed, when LibreOffice isn't installed).
1. **Single column.** Do not use side-by-side layout, even with tables. Multi-column resumes cause text-order scrambling in roughly half of ATS engines.
2. **No text boxes.** Many ATS parsers ignore text-box content entirely.
3. **No images.** This includes logos, headshots, and icon bullets. ATS cannot read them and they bloat file size.
4. **No tables for layout.** Tables for actual tabular data are fine, but don't use them to align dates against role titles. Use tab stops or right-aligned tabs instead.
5. **No headers / footers.** Some ATS skip these regions. Put name and contact info in the body of the document, top of page 1.
6. **Standard fonts only.** Calibri, Arial, Helvetica, or Times New Roman. Do not use display fonts, emoji, or embedded webfonts.
7. **Standard bullets.** Use `•` (Unicode bullet) or simple disc bullets via Word's bullet styles. Avoid arrows, checkmarks, dingbats.
8. **Standard section headings.** Use plain text: `Summary`, `Experience` (or `Work Experience` / `Professional Experience`), `Education`, `Skills`, `Certifications`. Avoid clever names like `My Journey` or `What I Bring`.
9. **Date format: `MM/YYYY - MM/YYYY`** (e.g., `08/2018 - Present`). Don't write "Aug 2018" or "August 2018"; some parsers fail on word months.
10. **Spell out acronyms first occurrence**, then abbreviate: `Continuous Integration / Continuous Deployment (CI/CD)`. After that, `CI/CD` alone is fine.
11. **No Unicode dashes - use plain hyphens (`-`) only.** Never use `–` (en-dash, U+2013) or `—` (em-dash, U+2014) anywhere in generated artifacts. Some ATS parsers render them as garbage characters or split the surrounding text into wrong fields. The build scripts (`build_resume_docx.py`, `build_cover_letter_docx.py`) auto-normalize BOTH `–` and `—` to `-` defensively, but bullet text should already be hyphen-only at the JSON layer. This rule applies to date ranges (`08/2018 - Present`), mid-sentence emphasis, and section dividers.

## Soft rules (follow unless there's a strong reason not to)

- **Body font size: 11pt.** Name: 14–18pt. Section headings: 12–14pt bold.
- **Margins: 0.5"–1" all sides.** Don't go below 0.5" or text gets cut on print.
- **Line spacing: single (1.0) or 1.15.** Avoid 1.5 or double; wastes space.
- **Active voice, past tense for prior roles, present tense for current role.**
- **Lead bullets with verbs, not "Responsible for".**
- **Quantify wherever truthful.** "$20K saved" beats "saved money."
- **Reverse chronological order** for work experience and education.
- **Keep links inline as plain text URLs.** Hyperlinks are fine but don't rely on them — print/PDF the resume mentally as you write.

## Filenames

Use `{Company}_{Position}_{YYYY-MM-DD}_Resume.docx`. ATS often rename on upload, but a clean filename helps the human reviewer and keeps the user's working folder tidy.

## What about graphics-heavy "modern" resume templates?

Skip them. They're optimized for human eyes (and Canva downloads). Most senior roles ship through Workday / Greenhouse / Lever ATSes — pure text wins every time. Save the visual flair for portfolio sites or LinkedIn.

## Skills section formatting

Group semantically and use one line per group with comma separation:

```
Cloud & Infrastructure: Azure, AKS, Docker, Kubernetes, Terraform, Linux
Languages: C#, .NET, Python, JavaScript, TypeScript, Angular, React
Architecture: Solution Architecture, Microservices, Event Sourcing, CQRS
```

This is more readable than a wall of comma-separated keywords AND parses cleanly into ATS skill fields. Lead with the group most relevant to the JD.

## Keyword matching

The JD's exact wording matters. If the JD says "Kubernetes" use "Kubernetes" — not "K8s" or "container orchestration". If the JD says "AWS" and the user's experience is Azure, do NOT write "AWS" — write "Azure" and call out cloud architecture transferability in the summary.

Do not stuff invisible white-text keywords. Some ATS detect this and reject. Modern parsers also ignore non-rendered text.

## Verifying the output

After generation:
- Open the DOCX in Word, Pages, or LibreOffice — make sure nothing is offset or hidden.
- Try copy-pasting into a plain-text editor — if a bullet drops or text scrambles, the layout is too clever.
- Check the .docx file size — if it's >100KB without images, something is bloated; investigate.
