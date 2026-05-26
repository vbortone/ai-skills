---
name: resume-tailor
description: Generate an ATS-friendly tailored resume, cover letter, and recruiter pitch against a specific job description. Use this skill whenever the user provides a job posting (URL or pasted text) and asks for a resume, application package, or wants to apply to a job - even if they just say "tailor a resume for this", "apply to this job", "draft an application", paste a JD with no instruction, or share a LinkedIn / Indeed / company-careers URL. Also triggers on phrases like "make a resume for", "customize my CV for", "I'm applying to", "what would my resume look like for", "write a cover letter for this role", or any combination of a job description and a request that implies application materials. The skill reads a `master_profile.md` from the user's working folder (their canonical career history, headlines, tailoring rules, and flags) and outputs a DOCX resume, DOCX cover letter, and a short recruiter pitch into a per-application subfolder.
---

# Resume Tailor

Generate ATS-friendly tailored application packages. Each invocation produces a resume, cover letter, and recruiter pitch tuned to one specific job description, drawing from the user's `master_profile.md` — their canonical career history, headline candidates, tailoring rules, and flags.

The skill is **user-agnostic**. Personal data — career, employers to anonymize, flag list — lives in the user's working folder, not the skill folder. See `examples/working-folder/` for the template a new user copies and fills in.

## When this skill applies

Trigger when the user supplies (or implies) a job posting and wants application materials. The job posting may arrive as:
- A pasted job description (full text)
- A URL to a job posting (LinkedIn, Indeed, company careers page, etc.)
- A description of a role (e.g., "Director of Engineering at a healthcare AI startup, $250K, remote") - in which case ask for the actual posting before generating

If the user only describes a role in general terms without a posting, ask for the actual JD text or URL before producing materials. Tailoring without a real JD is guessing.

## Inputs

1. **Job description** - required. URL or pasted text.
2. **Working folder** - the user's currently selected/mounted folder. Must contain `master_profile.md`. May also contain `tailor_config.json` (for anonymization patterns) — see `examples/working-folder/README.md`. Save outputs here.
3. **Optional preferences** - length override (1 page strict / 2 pages strict), title preference (which headline to lead with), tone (conservative / confident).

If the working folder doesn't contain `master_profile.md`, walk the user through bootstrapping from `examples/working-folder/master_profile.md.example`.

## Workflow

Follow these steps in order. Do not skip the freshness check.

### Step 0 - Load project context

Before generating anything, confirm the user's working-folder context is loaded. Claude Code's auto-memory conventions (`CLAUDE.md` for working memory, `memory/` for persistent memory) are loaded automatically at session start; the skill's own contract files (`master_profile.md`, `tailor_config.json`) are read in subsequent steps.

Use the auto-loaded project context throughout tailoring — it's how outputs sound like the user's voice instead of a generic template:

- **Vocabulary** — if `CLAUDE.md` or `memory/` contains program names, recurring internal terms, or domain jargon the user uses, reflect them in cover-letter prose. Don't translate them into generic language.
- **Active applications** — if the user is tracking active applications, surface relevant ones in `tailoring_notes.md` (e.g. re-applications to the same company, applications with the same recruiter).
- **Recruiter threads** — if the user is tracking recruiter conversations, cross-reference the JD's company against known threads and surface relevant anchors (comp range, last contact, role-fit signals) in the tailoring notes.
- **Open tasks / Someday items** — if the user maintains a tasks list, surface matches between the JD and any "someday" items the JD's domain could advance.
- **Prior outcomes** — if the user archives past applications with outcome notes, check whether the current JD's company is one the user has applied to before, and quote relevant lessons from those outcomes in the tailoring notes.
- **Comp targets** — if the user documents target compensation ranges by role tier (typically in `master_profile.md` → Tailoring Rules, `CLAUDE.md`, or a working-folder memory file), the comp-posture check in Step 1 uses them. If you can't find any documented target, ask the user before proceeding when the JD discloses comp.

If you expected context that's not there — for example the user mentioned a recruiter thread but no recruiter file is loaded — ask the user before proceeding to make sure they're in the right working folder.

The cross-references for active applications, recruiter threads, open tasks, and prior outcomes are owned by the sibling **`application-tracker`** skill. When it's loaded and the JD has a company name, invoke its three scripts to surface context before tailoring:

- `application-tracker/scripts/find_prior_applications.py --company "{Company}" --working-folder "{working_folder}"` — prior applications + outcome excerpts. Quote relevant outcomes in `tailoring_notes.md` → "Prior outcomes" section.
- `application-tracker/scripts/find_recruiter_threads.py --company "{Company}" --recruiters-file "{working_folder}/memory/people/recruiters.md"` — recruiter threads mentioning the company. Cite name, firm, last contact, comp anchor in `tailoring_notes.md` → "Recruiter context" section.
- `application-tracker/scripts/find_someday_matches.py --tasks-file "{working_folder}/TASKS.md" --keywords "{JD top keywords}"` — Someday items the JD's domain could advance. Surface in `tailoring_notes.md` → "Items to consider" section.

If `application-tracker` isn't loaded, use whatever's already in Claude Code's session context from `CLAUDE.md` / `memory/`.

### Step 1 - Confirm the JD

If the user pasted JD text, use it directly. If they gave a URL, fetch it through the following tiers in order — drop to the next tier only when the previous one fails or doesn't apply:

1. **Job-search MCP connectors first.** When the URL's domain matches a connected job-board MCP (LinkedIn, ZipRecruiter, Dice, Indeed, or any platform exposing `search_jobs` / `get_job_details` tools), use the connector. Structured JD data — title, location, comp, requirements — beats raw HTML scraping every time, and the comp field is what Step 0's comp-posture check reads.
2. **WebFetch second.** Plain HTTP fetch with readability extraction. Works for most company-careers pages and bare JD pastes-as-URL.
3. **Claude in Chrome third.** When WebFetch returns paywalled / login-required / JS-rendered content, try `mcp__Claude_in_Chrome__navigate` + `mcp__Claude_in_Chrome__get_page_text`. LinkedIn jobs pages, in particular, are reliably blocked by WebFetch but reachable through Chrome.
4. **Ask the user to paste fourth.** Only when tiers 1-3 all fail or don't apply. Tell the user which tier failed and why; never invent or summarize from a stub.

Once you have the JD, confirm with the user: *"I see this is for {Position} at {Company}. Want me to proceed?"* — proceed unless they correct.

**Comp-posture check (when the JD discloses comp).** If the JD includes a salary range, total comp, or equity disclosure, compare against the user's documented comp targets (loaded in Step 0). Categorize the JD's range as **above target**, **at target**, **below target**, or **not disclosed**, and surface the finding BEFORE proceeding to tailor:

- If **below target**: tell the user explicitly and give them a chance to abort cheaply. For example: *"The JD discloses $X-$Y. Your documented target for this tier is $Z — below target. Want to proceed and tailor anyway, or pass?"* Do not generate the full package without that confirmation.
- If **at** or **above target**: note it and proceed.
- If **not disclosed**: note that too and proceed; the package can still get written without disclosure.
- If no comp targets are documented anywhere in the working folder, ask the user before proceeding — they may not have one and that's fine, but the answer should be explicit, not guessed.

Record the comp-posture finding at the top of `tailoring_notes.md` regardless of which branch fired — it's the single most decision-relevant fact about the application.

Extract from the JD:
- Company name (sanitize for filenames)
- Position title (sanitize for filenames)
- Required vs. preferred qualifications
- Key responsibilities
- Hard-requirement keywords (technologies, methodologies, certifications, years of experience)
- Soft signals (tone, scale, "fast-paced startup" vs. "Fortune 500 governance")
- Compensation and location (record but don't put on resume)

### Step 2 - Master profile freshness check

The skill reads `master_profile.md` from the working folder, last refreshed on the date recorded in its frontmatter. The freshness helper (`scripts/refresh_profile.py`) walks the working folder and reports any context-bearing file (`.md`, `.txt`, `.json`, `.yaml`, `.docx`) with an mtime newer than `last_refreshed`. By default it skips generated content (`Applications/`, `Archive/`) and tooling directories (`.git/`, `.venv/`, `node_modules/`, `__pycache__/`, dotfiles).

Run the freshness check. If any file is reported newer than `last_refreshed`:
1. Tell the user: *"Your working folder has been updated since I last refreshed the master profile (N files newer). Want me to refresh before tailoring?"*
2. If yes — re-read the changed files, propose updates to `master_profile.md`, get user approval, then update both the file and its `last_refreshed` field, then proceed.
3. If no — proceed with the existing profile but note the staleness in the tailoring notes file.

If `last_refreshed` is missing from the frontmatter, treat the profile as stale and offer to set it after the user reviews.

### Step 3 - Tailor

Read `master_profile.md` and `references/tailoring_playbook.md`. Construct a tailored resume by:

1. **Headline** - pick from the user's Headline Candidates (in `master_profile.md` → Identity) the closest match to the target role. Don't invent new titles.
2. **Summary (3-4 sentences)** - open with years of experience and the strongest credibility signal for this role. Echo 2-3 high-priority JD keywords if truthful.
3. **Skills section** - reorder the skills inventory so the JD-required skills lead. Keep groups; don't pad with skills the user doesn't have.
4. **Experience bullets** - for each role, select bullets from the master profile that align with the JD, and rewrite them so the JD's verbs and nouns appear where truthful. Lead each bullet with the impact (number, scale, outcome) when available.
5. **Length, work-history scope, bullet counts, archetype mappings** - all user-specific. Read `master_profile.md` → **Tailoring Rules** for the user's policy on these. If the user's Tailoring Rules section is missing or doesn't cover the decision at hand, ASK the user once before generating, and offer to record the answer back to their Tailoring Rules section for future runs. Do not guess defaults.
6. **Education + certifications** - include entries from `master_profile.md` per the user's Tailoring Rules. For certifications, lead with whichever match the JD.
7. **Honesty rules** - never invent dates, employers, certifications, or metrics. Use the **Flags & Items to Confirm Before Use** section of `master_profile.md` to avoid overclaims. Re-read it before every generation.

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
  - **Anonymization** — patterns come from `{working_folder}/tailor_config.json` (auto-discovered via walk-up from the output directory, or pass `--config <path>`). Fails (exit code 1) if any pattern matches the rendered DOCX. If no config or no patterns, the check is skipped with an info note. If the target JD employer is one of the anonymized employers and naming them is correct, pass `--skip-anonymization` to the build scripts and note it in the report.
  - **Page count** — renders the DOCX to PDF via docx2pdf (requires MS Word) and fails (exit code 2) if the resume exceeds 2 pages or the cover letter exceeds 1 page. Pass `--no-strict-pages` to downgrade to a warning, or `--skip-page-check` when Word isn't available.
- Any flags raised (e.g., "JD asks for 5+ years of GCP — your profile shows Azure depth, not GCP. I led with Azure cloud-architecture experience and noted multi-cloud transferability rather than claim GCP.")

## Critical rules

- **Honesty first.** If the JD demands something the user doesn't have, do not invent it. Lead with the closest adjacent skill and flag the gap in `tailoring_notes.md` so they can decide whether to apply.
- **Anonymize per the user's rules.** Every resume / cover letter / recruiter pitch must respect the Anonymization Rule documented in the user's `master_profile.md` and enforced by `tailor_config.json`. The post-render verifier hard-fails the build if any forbidden token appears in the output. Inversion: if the JD employer matches one of the anonymized employers, pass `--skip-anonymization` to the build scripts.
- **Single source of truth.** All facts come from `master_profile.md`. Do not pull facts from training memory of "what's on a typical Director resume."
- **Respect every Flag.** The "Flags & Items to Confirm Before Use" section of `master_profile.md` lists items that must NOT appear on a resume or require specific framing. Re-read this section before generating each output.
- **Keep originals.** Do not modify `master_profile.md` outside the freshness-refresh flow, and never overwrite a previous Application folder for the same company+position+date - increment the date or add `_v2`.
- **ATS-safe.** No tables-for-layout, no text boxes, no headers/footers, no images. **Use plain hyphens (`-`) only - never use Unicode dashes like en-dash (U+2013) or em-dash (U+2014) - some ATS parsers render them as garbage.** See `references/ats_rules.md` for the full list. Build scripts auto-normalize both Unicode dashes defensively.
- **Hard cap 2 pages on resumes.** Never spill to page 3. If long, trim per the user's "Tailoring Rules" in `master_profile.md`. See "Length decisions" in `references/tailoring_playbook.md`.
- **Hard cap 1 page on cover letters.** 2-3 paragraphs, ~250-300 words. Use 2 when hook + experience fuse cleanly; 3 when there's a real differentiator or gap to address. See `references/cover_letter_guide.md`.
- **Work-history scope is user-defined.** Always follow the user's "Tailoring Rules" section in `master_profile.md` for which employers to always include vs. default-off vs. cover-letter-context-only. If the user has not documented a rule for a decision, ASK them rather than guessing.
- **Consolidate multi-role same-company entries.** When the user held multiple roles at one company, render as a single entry under the senior title with the FULL date span; merge bullets from junior and senior roles. See "Multi-role consolidation" in `references/tailoring_playbook.md`.

## Reference files

Read these as needed during a run; they're not always required:

- `{working_folder}/master_profile.md` - The user's canonical work history, headlines, tailoring rules, and flags. **Always read.** If absent, walk the user through bootstrapping from `examples/working-folder/master_profile.md.example`.
- `{working_folder}/tailor_config.json` - Anonymization patterns enforced by the post-render verifier. Optional — see `examples/working-folder/tailor_config.json.example`.
- `references/ats_rules.md` - DOCX formatting rules for ATS safety. Read before generating the DOCX.
- `references/tailoring_playbook.md` - How to map JD requirements to bullets. Read during tailoring.
- `references/cover_letter_guide.md` - Cover letter structure. Read when generating cover letter.
- `references/recruiter_pitch_guide.md` - Recruiter pitch format. Read when generating pitch.
- `scripts/build_resume_docx.py` - DOCX generator. Pass tailored content as JSON via stdin.
- `scripts/build_cover_letter_docx.py` - Cover letter DOCX generator.
- `scripts/verify_output.py` - Post-render anonymization + page-count verifier. Invoked automatically by the build scripts.
- `scripts/refresh_profile.py` - Freshness check helper.
- `examples/working-folder/` - Template a new user copies into their working folder to bootstrap.

## Refreshing the master profile

When the user adds new experience or wants to update facts, refresh the profile rather than putting one-off edits inside generated resumes:

1. Read the new source material the user provides (file, paste, or new entries in the source folder).
2. Propose specific updates to `master_profile.md` (sections affected, before/after diffs).
3. After user approval, edit `master_profile.md` and update the `last_refreshed` field in the frontmatter.
4. Append an entry to the Refresh Log section with date and a 1-line summary of the change.
5. Do NOT delete prior entries - additive only - unless the user explicitly says a fact was wrong.

## Edge cases

- **JD URL is LinkedIn jobs page** - WebFetch is reliably blocked. Try Claude in Chrome MCP (`mcp__Claude_in_Chrome__navigate` + `get_page_text`) before asking the user to paste. See Step 1 fetch order.
- **JD is a screenshot** - read the image, transcribe, confirm transcription with user.
- **Multi-role JD ("we're hiring for several positions")** - ask which position to target before proceeding.
- **JD demands certifications the user doesn't have** - list adjacent ones; flag in tailoring notes.
- **Re-applying to the same company+position** - name file with `_v2` suffix and reference prior tailoring notes.
- **Working folder not selected** - fall back to outputs folder, but warn the user the deliverables won't be saved with the rest of their application history. Better to ask the user to select / mount their working folder first.
- **No `master_profile.md` in working folder** - offer to bootstrap from `examples/working-folder/master_profile.md.example`. Do not generate outputs against a stub profile.
