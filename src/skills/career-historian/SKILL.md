---
name: career-historian
description: Build and grow a deep, per-employer knowledge base ("dossiers") of the user's job history through document ingestion, MCP data sources, and looped interviews — projects, skills evidence, and key contacts/references per company. Use this skill whenever the user wants to record, document, or be interviewed about their employment history or past work, even if they don't say "interview" — "let's document my time at {Company}", "add this old resume to my career history", "capture the projects I did at X", "who could I use as a reference from Y", "update my career dossier", "where did we leave off on my job history", "I want to build a tome/archive of my career". Also trigger when the user shares an old resume, performance review, project doc, or LinkedIn export and wants it mined for career facts. The dossiers this skill builds are the deep source material behind the sibling resume-tailor skill's master_profile.md; this skill itself never generates resumes or application materials.
---

# Career Historian

Accumulate a deep, durable knowledge base of the user's employment history — one dossier per employer — through three intake channels: documents the user provides, data reachable over MCP, and a looped interview process. The goal is a "tome" exhaustive enough that the sibling `resume-tailor` skill can tailor tightly against any JD without the user re-remembering their career every time.

The skill is **user-agnostic**. Personal data — employers, projects, contacts, stories — lives in the user's chosen destination (their working folder or their own knowledge vault via MCP), never in the skill folder. See `examples/working-folder/` for the bootstrap templates.

## What a dossier is

One Markdown file per employer capturing, at minimum:

- **Projects** — what was built/run/fixed, the user's role, tech, team scale, outcomes with numbers, and story-grade detail (the STAR material behavioral interviews need).
- **Skills evidence** — each skill tied to where it was actually exercised. A skill without evidence is a keyword; a skill with evidence is a resume bullet waiting to happen.
- **Contacts** — colleagues, managers, and stakeholders the user may want as references or talking points, with relationship context.
- **Open questions** — gaps the gap-analysis pass found, queued for the next session.
- **Provenance on every fact** — which interview date or source document each fact came from.

The canonical structure is `examples/working-folder/career-history/company_dossier.md.example`. Follow it when creating new dossiers so `scripts/dossier_status.py` can parse coverage.

## Relationship to resume-tailor

This skill is **upstream** of `resume-tailor` and writes only dossiers:

- It does NOT edit `master_profile.md`. The user syncs manually: resume-tailor's freshness check (`refresh_profile.py`) notices new/changed files in the working folder and offers to distill them into the profile through its approval-gated refresh flow.
- To make that handoff work even when dossiers live outside the working folder (MCP destination), this skill always updates a local `career-history/INDEX.md` in the working folder at session end (see Step 5). That file is what the freshness check sees.
- Dossier content follows the same honesty contract resume-tailor enforces: nothing invented, estimates labeled as estimates, provenance traceable.

## Inputs

1. **Working folder** — the user's job-search folder (same one resume-tailor uses). Holds `historian_config.json` and the local `career-history/` directory (or just `INDEX.md` when dossiers live elsewhere).
2. **`historian_config.json`** — where dossiers live. See `examples/working-folder/historian_config.json.example`. Two destination types:
   - `local` — a directory path. Relative paths resolve against the working folder (default `career-history/`); absolute paths are allowed so users can point inside e.g. an Obsidian vault on disk.
   - `mcp` — a named MCP server + base path (e.g. an Obsidian or vault connector). The skill reads/writes dossiers through that server's note tools instead of the filesystem.
3. **Optional source material** — old resumes, performance reviews, LinkedIn exports, project docs, or MCP-reachable data the user wants mined.

## Workflow

### Step 0 — Load config and destination

Read `historian_config.json` from the working folder.

- **Missing config**: this is a first run. Ask the user where dossiers should live — default local `career-history/` inside the working folder, an absolute local path (e.g. into their notes vault), or an MCP destination. Bootstrap the config from `examples/working-folder/historian_config.json.example`, then continue.
- **MCP destination**: verify the named server's tools are actually reachable (load them via ToolSearch if deferred). If they aren't, tell the user and offer the local fallback rather than silently writing nowhere.

### Step 1 — Pick the target company

Build a coverage map before asking what to work on, so the user chooses from facts instead of memory:

- Local destination: run `scripts/dossier_status.py --history-dir "{resolved_history_dir}"` — it returns per-company section coverage, open-question counts, and `last_interviewed` dates as JSON.
- MCP destination: list and skim the dossiers through the server's tools and assemble the same picture.
- If `master_profile.md` exists in the working folder, diff its Work History employers against existing dossiers. Employers with **no dossier at all** are the highest-value suggestions.

Present the map briefly (companies, what's thin, what's stale) and let the user pick. A brand-new company gets a dossier created from the template with whatever frontmatter facts the user gives up front (titles, dates, location).

### Step 2 — Ingest sources before interviewing

Ask once: *"Any documents or sources I should mine first — old resumes, performance reviews, LinkedIn export, project docs, anything reachable through a connector?"*

Interview time is the scarce resource. Never ask the user to recall what a document already states — mine documents first, then spend the interview on what documents can't hold: stories, metrics, context, contacts.

For each source:
1. Read it (file, paste, or MCP fetch).
2. Extract facts into the relevant dossier sections, each tagged with its source (e.g. `Source: resume_2019.docx`).
3. Confirm extractions with the user as a single batch summary — "here's what I pulled, anything wrong?" — not item-by-item interrogation.

If there are no sources, skip straight to Step 3.

### Step 3 — Interview loops

Three tracks, in default order **projects → skills → contacts** (the user can reorder or skip). Read `references/interview_guide.md` before the first loop of a session — it holds the question banks and probing techniques.

Loop mechanics, which are the heart of this skill:

- **One question at a time.** Never a wall of questions. The user is recalling, not filling out a form.
- **Capture immediately.** After each answer, write it into the dossier (or a staging buffer you flush at natural pauses). Nothing the user says should be lost to a crash or a context window.
- **Then re-prompt the loop**: *"Another project from your {Company} years, or move on?"* / *"Anyone else worth recording?"* Keep looping until the user says stop — "stop", "done", "that's it", "move on", "enough for today" all mean stop. Respect it on the first signal; don't squeeze in one more question.
- **Probe each item lightly on the first pass** — 2 to 4 follow-ups maximum (outcome numbers, the user's specific role, timeframe). Depth comes from the gap-analysis pass in Step 4, not from exhausting the user per item.
- **Quantify, but honestly.** Push gently for numbers ("roughly how many users / how much faster / what was the budget?"). When the user can only estimate, record the estimate marked as one: `~40% (user's recollection)`.

Per-track focus:

- **Projects**: problem, the user's role, team size/shape, tech and methods, outcome with numbers, dates, and one story-worthy moment (conflict, save, decision) per project when it surfaces naturally.
- **Skills**: name the skill, then anchor it — *where* did they exercise it, at what depth, how recently. Cross-link to projects already captured instead of re-asking.
- **Contacts**: name, title then and now (if known), relationship, what they worked on together, reference potential (yes / maybe / no and why), current contact info if the user has it.

### Step 4 — Gap-analysis review (the thinking pass)

After the loops — or whenever the user pauses — review the full dossier deliberately and generate the follow-up questions a good biographer would ask. This is where the dossier goes from "list of things" to "tome".

- If subagents are available, spawn a general-purpose agent with the dossier content plus `references/gap_analysis_guide.md`, asking for prioritized follow-up questions as structured output. A fresh agent reads the dossier without the interview's momentum and spots gaps the interviewer is blind to.
- If not, do the review pass yourself: re-read the dossier top to bottom against the gap categories in `references/gap_analysis_guide.md` (unquantified outcomes, skills without evidence, date gaps, contacts without relationship context, missing scale/leadership/budget angles, incomplete stories).

Then split the resulting questions:

- Ask the **top 3–5 now**, one at a time, while the user's memory is warm.
- Write the rest into the dossier's **Open questions** section with today's date. They are the agenda for the next session — Step 1's coverage map surfaces their count.

### Step 5 — Save and index

- Write the dossier to its destination (filesystem Write for `local`, the server's note-write tool for `mcp`).
- Append a one-line entry to the dossier's **Interview log** (date + what was covered + counts).
- Update `{working_folder}/career-history/INDEX.md` — one line per company: dossier location, `last_interviewed`, open-question count. **Always local, always touched at session end**, even when dossiers live in MCP. This is the bridge that lets resume-tailor's freshness check discover that new history exists.

### Step 6 — Wrap up

End the session with:

- A short summary of what was captured: N projects, N skills, N contacts, N open questions queued.
- Where it was saved (path or vault location).
- A reminder that dossiers don't auto-flow into `master_profile.md`: the next resume-tailor run's freshness check will offer to distill, or the user can ask explicitly ("refresh my master profile from my career history") any time.

## Critical rules

- **Capture only what the user said or a source states.** Never embellish, round up, or fill silence with plausible facts. The dossier feeds resumes whose honesty contract depends on this. Estimates are recorded as estimates with attribution.
- **Stop means stop.** Loops end on the user's first stop signal. Progress is saved immediately, so any session is resumable — make that true by flushing captures at every natural pause.
- **One question at a time.** A form-like barrage produces shallow answers and user fatigue. The looped single-question rhythm is the product.
- **Additive, never destructive.** Don't delete prior dossier content. When the user corrects a fact, update it and note the correction in the Interview log if it's material (dates, employers, metrics).
- **Contacts are sensitive personal data.** They live only in the user's destination. Never copy contact details into anything that leaves the working folder/vault, and never into the skill folder.
- **Provenance on every fact.** Each project, skill row, and contact carries a `Source:` line (interview date or document name). Resume-tailor's "single source of truth" discipline only works if facts are traceable.
- **No resume output.** If the user pivots to "now make me a resume", hand off to `resume-tailor` — don't generate application materials from this skill.

## Edge cases

- **No working folder selected** — ask the user to select/mount their job-search working folder first; the config and INDEX.md must live somewhere persistent.
- **Config points at an MCP server that isn't connected** — say so, offer local fallback or fixing the connection. Never silently degrade.
- **User wants to interview about a company already richly documented** — start from its Open questions instead of the standard track order; tell them that's what you're doing.
- **Mid-loop pivot ("actually, about my time at {other company}…")** — flush the current dossier, switch dossiers, keep going. Note the partial loop in both Interview logs.
- **Document contradicts what the user said in interview** — surface the discrepancy and let the user adjudicate; record the resolution. Don't silently prefer either source.
- **User offers confidential material (NDA'd project details, proprietary metrics)** — capture what they volunteer, but flag it in the dossier (`⚠ confidential — confirm framing before resume use`) so resume-tailor's Flags discipline can pick it up during sync.

## Reference files

- `references/interview_guide.md` — question banks per track, probing techniques, loop etiquette. Read before the first interview loop of a session.
- `references/gap_analysis_guide.md` — gap categories and the follow-up-question output format. Read (or hand to the subagent) in Step 4.
- `scripts/dossier_status.py` — coverage report over a local history dir; JSON on stdout. Read-only.
- `examples/working-folder/` — bootstrap templates: config, dossier template, INDEX template, README.
