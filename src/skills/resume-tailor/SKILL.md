---
name: resume-tailor
description: Generate an ATS-friendly tailored resume, cover letter, and recruiter pitch for Vincent Bortone against a specific job description. Use this skill whenever the user provides a job posting (URL or pasted text) and asks for a resume, application package, or wants to apply to a job - even if they just say "tailor a resume for this", "apply to this job", "draft an application", "this PwC role looks interesting", paste a JD with no instruction, or share a LinkedIn / Indeed / company-careers URL. Also triggers on phrases like "make a resume for", "customize my CV for", "I'm applying to", "what would my resume look like for", "write a cover letter for this role", or any combination of a job description and a request that implies application materials. The skill draws from a bundled master profile (Vincent's full work history) and outputs a DOCX resume, DOCX cover letter, and a short recruiter pitch into the user's working folder, organized into a per-application subfolder.
---

# Resume Tailor

Generate ATS-friendly tailored application packages for Vincent Bortone. Each invocation produces a resume, cover letter, and recruiter pitch tuned to one specific job description, drawing from a curated master profile of Vincent's career.

## When this skill applies

Trigger when the user supplies (or implies) a job posting and wants application materials. The job posting may arrive as:
- A pasted job description (full text)
- A URL to a job posting (LinkedIn, Indeed, company careers page, etc.)
- A description of a role (e.g., "Director of Engineering at a healthcare AI startup, $250K, remote") - in which case ask for the actual posting before generating

If the user only describes a role in general terms without a posting, ask for the actual JD text or URL before producing materials. Tailoring without a real JD is guessing.

## Inputs

1. **Job description** - required. URL or pasted text.
2. **Working folder** - the user's currently selected/mounted folder. Save outputs there.
3. **Optional preferences** - length override (1 page strict / 2 pages strict), title preference (which headline to lead with), tone (conservative / confident).

## Workflow

Follow these steps in order. Do not skip the freshness check.

### Step 1 - Confirm the JD

If the user pasted JD text, use it directly. If they gave a URL:
1. Fetch the URL.
2. If fetch fails (paywalled, login-required like LinkedIn job pages, JS-rendered) tell the user clearly and ask them to paste the JD text. Do not invent or summarize from a stub.
3. Once you have the JD, confirm with the user: *"I see this is for {Position} at {Company}. Want me to proceed?"* - proceed unless they correct.

Extract from the JD:
- Company name (sanitize for filenames)
- Position title (sanitize for filenames)
- Required vs. preferred qualifications
- Key responsibilities
- Hard-requirement keywords (technologies, methodologies, certifications, years of experience)
- Soft signals (tone, scale, "fast-paced startup" vs. "Fortune 500 governance")
- Compensation and location (record but don't put on resume)

### Step 2 - Master profile freshness check

The skill reads a `master_profile.md` in the working folder, last refreshed on a known date. The user's source materials live at `C:\Users\vbort\OneDrive\Documents\0-Projects\New Job Search\Source\` (when the New Job Search folder is selected - otherwise the canonical location may differ; ask if uncertain).

Before generating, run the freshness check (see `scripts/refresh_profile.py`). If any source file in the Source folder has an mtime newer than the master profile's `last_refreshed` timestamp:
1. Tell the user: *"Your Source folder has been updated since I last refreshed the master profile. Want me to refresh before tailoring?"*
2. If yes - re-read the changed sources, propose updates to `master_profile.md`, get user approval, then update both the file and its `last_refreshed` field, then proceed.
3. If no - proceed with the existing profile but note the staleness in the tailoring notes file.

If the working folder is not the New Job Search project (Source folder unreachable), skip the check silently and proceed.

### Step 3 - Tailor

Read `master_profile.md` and `references/tailoring_playbook.md`. Construct a tailored resume by:
1. **Headline** - pick from the Headline Inventory the closest match to the target role. Don't invent new titles.
2. **Summary (3-4 sentences)** - open with years of experience and the strongest credibility signal for this role. Echo 2-3 high-priority JD keywords if truthful.
3. **Skills section** - reorder the skills inventory so the JD-required skills lead. Keep groups; don't pad with skills he doesn't have.
4. **Experience bullets** - for each role, select bullets from the master profile that align with the JD, and rewrite them so the JD's verbs and nouns appear where truthful. Lead each bullet with the impact (number, scale, outcome) when available.
5. **Length** - default 1-2 pages, model decides. Director / architect / leadership roles: 2 pages. Specialized IC roles: 1 page. Always include current Cognizant role; condense Wachtell to highlights for 1-page; keep more Wachtell detail for 2-page.
6. **Education + certifications** - always include UCF MS FinTech (3.9 GPA) and Cornell BS. For certifications, lead with whatever matches the JD (Azure, AI/Claude, GitHub Copilot, MongoDB).
7. **Honesty rules** - never invent dates, employers, certifications, or metrics. Use the Flags section of the master profile to avoid overclaims (especially the 15% AI productivity number, FlowSource ownership, AI POC authorship).

### Step 4 - Generate DOCX

Use `scripts/build_resume_docx.py`. It accepts a JSON description of the tailored resume and produces an ATS-safe DOCX:
- Single-column layout, no text boxes, no images, no tables for layout
- Calibri 11pt body, 14-16pt name, 12pt headings
- Standard section headings: Summary, Experience, Education, Skills, Certifications
- Simple bullets (•), MM/YYYY dates, US English
- See `references/ats_rules.md` for the full rule set

### Step 5 - Cover letter + recruiter pitch

Generate both in the same run unless the user opts out:
- **Cover letter** - `scripts/build_cover_letter_docx.py`. 3-4 paragraphs: opening hook, 2 paragraphs of relevant experience tied to JD priorities, closing call-to-action. Read `references/cover_letter_guide.md`.
- **Recruiter pitch** - 3-4 sentences saved as Markdown. For phone screens and recruiter outreach. Read `references/recruiter_pitch_guide.md`.

### Step 6 - Save outputs

Create a per-application subfolder so the working folder stays organized:

```
{working_folder}/Applications/{Company}_{Position}_{YYYY-MM-DD}/
├── {Company}_{Position}_{YYYY-MM-DD}_Resume.docx
├── {Company}_{Position}_{YYYY-MM-DD}_CoverLetter.docx
├── recruiter_pitch.md
├── job_description.txt          (verbatim JD captured at apply-time - JDs vanish from the web)
└── tailoring_notes.md           (what was emphasized, what was de-emphasized, flags raised)
```

**Filename sanitization:**
- Replace spaces with underscores
- Strip characters not in `[A-Za-z0-9_-]`
- Truncate company / position to 50 chars each
- Date is the date the resume is generated, in `YYYY-MM-DD` format

If `Applications/` doesn't exist yet, create it.

### Step 7 - Report back

End the response with:
- A `computer://` link to the per-application subfolder
- A 2-sentence summary of what was tailored (headline chosen, top 3 emphasized themes)
- Confirmation that post-render compliance checks passed. The build scripts automatically run two checks (see `scripts/verify_output.py`) and emit a JSON report on stdout:
  - **Anonymization** — fails (exit code 1) if `PwC`, `pwc.com`, or `PricewaterhouseCoopers` appear in the rendered DOCX. If the target JD is PwC itself, pass `--allow-pwc` to the build scripts to skip this check and note it in the report.
  - **Page count** — renders the DOCX to PDF via docx2pdf (requires MS Word) and fails (exit code 2) if the resume exceeds 2 pages or the cover letter exceeds 1 page. Pass `--no-strict-pages` to downgrade to a warning, or `--skip-page-check` when Word isn't available.
- Any flags raised (e.g., "JD asks for 5+ years of GCP - your profile shows Azure depth, not GCP. I led with Azure cloud-architecture experience and noted multi-cloud transferability rather than claim GCP.")

## Critical rules

- **Honesty first.** If the JD demands something Vincent doesn't have, do not invent it. Lead with the closest adjacent skill and flag the gap in `tailoring_notes.md` so he can decide whether to apply.
- **Anonymize the client.** Every resume / cover letter / recruiter pitch must refer to Vincent's engagement client as "Big 4 Accounting Firm" or "Big 4 professional services client" - never name PwC. See the Anonymization Rule in `master_profile.md` for the full substitution table. Inversion: if the JD is from PwC, name PwC because it's the target employer.
- **Single source of truth.** All facts come from `master_profile.md`. Do not pull facts from training memory of "what's on a typical Director resume."
- **Respect every Flag.** The Flags section of the master profile lists items that must NOT appear on a resume - including: AI Hooks framework (proposal-only, never implemented), MongoDB Certified Developer (removed at user direction), 15% AI productivity number as personal claim, AI POC personal authorship language, FlowSource personal authorship language, NGA delivery engagement. Re-read the Flags section before generating each output.
- **Keep originals.** Do not modify `master_profile.md` outside the freshness-refresh flow, and never overwrite a previous Application folder for the same company+position+date - increment the date or add `_v2`.
- **ATS-safe.** No tables-for-layout, no text boxes, no headers/footers, no images. **Use plain hyphens (`-`) only - never use Unicode dashes like en-dash (U+2013) or em-dash (U+2014) - some ATS parsers render them as garbage.** See `references/ats_rules.md` for the full list. Build scripts auto-normalize both Unicode dashes defensively.
- **Hard cap 2 pages on resumes.** Never spill to page 3. If long, cut Wachtell bullets first, then older Cognizant bullets, then shorten the longest line. See the "Length decisions" section of `references/tailoring_playbook.md`.
- **Hard cap 1 page on cover letters.** 2-3 paragraphs, ~250-300 words. Use 2 when hook + experience fuse cleanly; 3 when there's a real differentiator or gap to address. See `references/cover_letter_guide.md`.
- **Default work-history scope.** Always include Cognizant and Wachtell. Always EXCLUDE J.P. Morgan and Mercer Management Consulting unless Vincent explicitly asks for them. See Step 4 of `references/tailoring_playbook.md`.
- **Consolidate multi-role same-company entries.** Render Cognizant and Wachtell as a single entry per company under the senior title with the FULL date span; merge bullets from junior and senior roles.

## Reference files

Read these as needed during a run; they're not always required:

- `{Working Folder}/master_profile.md` - Vincent's canonical work history. Always read.  Should be in the working folder, if not, generate one from the source files.
- `references/ats_rules.md` - DOCX formatting rules for ATS safety. Read before generating the DOCX.
- `references/tailoring_playbook.md` - How to map JD requirements to bullets. Read during tailoring.
- `references/cover_letter_guide.md` - Cover letter structure. Read when generating cover letter.
- `references/recruiter_pitch_guide.md` - Recruiter pitch format. Read when generating pitch.
- `scripts/build_resume_docx.py` - DOCX generator. Pass tailored content as JSON via stdin.
- `scripts/build_cover_letter_docx.py` - Cover letter DOCX generator.
- `scripts/refresh_profile.py` - Freshness check helper.

## Refreshing the master profile

When the user adds new experience or wants to update facts, refresh the profile rather than putting one-off edits inside generated resumes:

1. Read the new source material the user provides (file, paste, or new entries in the Source folder).
2. Propose specific updates to `master_profile.md` (sections affected, before/after diffs).
3. After user approval, edit `master_profile.md` and update the `last_refreshed` field in the frontmatter.
4. Append an entry to the Refresh Log section with date and a 1-line summary of the change.
5. Do NOT delete prior entries - additive only - unless the user explicitly says a fact was wrong.

## Edge cases

- **JD URL is LinkedIn jobs page** - almost always blocked. Ask user to paste.
- **JD is a screenshot** - read the image, transcribe, confirm transcription with user.
- **Multi-role JD ("we're hiring for several positions")** - ask which position to target before proceeding.
- **JD demands certifications Vincent doesn't have** - list adjacent ones; flag in tailoring notes.
- **Re-applying to the same company+position** - name file with `_v2` suffix and reference prior tailoring notes.
- **Working folder not selected** - fall back to outputs folder, but warn the user the deliverables won't per