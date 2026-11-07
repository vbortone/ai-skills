# Tailoring Playbook

How to map a job description onto the user's `master_profile.md` and produce a resume that reads like it was written for that specific job.

## Tailoring is editing, not invention

Tailoring means selecting and rephrasing what's already in `master_profile.md`. Inventing experience to match a JD is fabrication, ends careers, and makes you a worse advisor. If the JD asks for something the user doesn't have, the right move is to call out the closest adjacent experience and flag the gap so the user can decide whether to apply.

## Anonymize per the user's rules (hard rule)

If the user's `master_profile.md` documents an Anonymization Rule, **every generated artifact (resume, cover letter, recruiter pitch) must respect it.** Code-level enforcement lives in `tailor_config.json` and is checked by the post-render verifier (`scripts/verify_output.py`), but you should anonymize correctly *while writing*, not rely on the verifier catching mistakes. Inversion: if the JD employer matches one of the anonymized employers, naming them is correct and the build scripts should be invoked with `--skip-anonymization`.

## Respect the Flags section before every output

Before any bullet ships, scan the user's `master_profile.md` → **Flags & Items to Confirm Before Use** section. Apply every framing rule documented there unconditionally. Re-read this section before every generation — it's the user's accumulated wisdom about what they will not stand behind on a resume.

## Step-by-step

### 1. Decode the JD

Read the JD twice. First pass to understand the role; second pass to extract structured signals.

Pull out:
- **Title and seniority** — "Director of Engineering" vs. "Staff Engineer" vs. "Solution Architect" demand different framings of the same career.
- **Must-haves** — anything in "Required" / "Minimum qualifications" / "5+ years of X". These are ATS gates.
- **Nice-to-haves** — "Preferred" / "Bonus". These differentiate, not gate.
- **Technical stack** — exact technology names (Azure / AWS / GCP, .NET / Java, Angular / React, Kubernetes / ECS).
- **Methodology signals** — "Agile", "SAFe", "DevOps", "Platform engineering".
- **Domain signals** — financial services, audit/assurance, healthcare, AI/ML.
- **Leadership scope** — "manages a team of N", "owns roadmap", "individual contributor".
- **Cultural signals** — "fast-paced startup" implies different bullet emphasis than "Fortune 500 governance".

### 2. Pick the headline

From the user's **Headline Candidates** (in `master_profile.md` → Identity), choose the single closest match to the JD title and seniority. The user's "Tailoring Rules" section may include explicit JD-archetype-to-headline mappings — follow them when present.

Don't invent a brand-new title. Pick one from the inventory.

### 3. Write the summary (3-4 sentences)

Formula:
1. **Sentence 1:** years of experience + the strongest credibility signal that aligns with the JD.
2. **Sentence 2:** 2-3 high-impact themes from the JD's responsibilities, each tied to a specific track-record bullet from the user's history.
3. **Sentence 3:** a quantified achievement (preferably one that aligns with the JD's domain).
4. **Optional sentence 4:** differentiator (specialized credential, advanced degree, distinctive prior role) only if it strengthens the case for THIS role.

Echo 2-3 of the JD's exact keywords if they're truthful. Don't shoehorn.

### 4. Order and rewrite the experience

**Work-history scope is user-defined.** Read `master_profile.md` → **Tailoring Rules** for which employers always appear on the resume, which are default-off, and which are cover-letter-context-only. If the user's Tailoring Rules section is missing or silent on a decision, ASK the user before generating — do not guess from a skill-side default. Offer to record the answer back to their Tailoring Rules section so future runs don't ask again.

**Bullet count per entry is user-defined.** Same rule: read `master_profile.md` → Tailoring Rules. If silent, ask the user once and offer to record.

**Consolidate multi-role same-company entries to the senior title (process, not policy):**
When the user held multiple roles at the same company, render them as a SINGLE consolidated entry on the resume:
- **Title** = the most senior title held.
- **Dates** = the FULL span (junior-role start through senior-role end / Present).
- **Context** = optional one-line note acknowledging the promotion path if it strengthens the case. Skip if it adds clutter.
- **Bullets** = pull from BOTH the senior and junior roles, picking the strongest impact bullets across the entire tenure. Hard-dollar wins and quantified outcomes from the junior role are usually worth keeping. The senior bullets typically lead.

Rationale: visual fragmentation hurts readability, and a single multi-year entry showing progression reads stronger than two separate entries that look like job-hopping. The cover letter and recruiter pitch can still surface the promotion arc verbatim.

Rewrite each bullet so:
- It opens with a verb (Led, Architected, Reduced, Implemented).
- It states the **impact** before the activity if the impact is quantified.
- It uses the JD's wording where truthful — if the JD says "Kubernetes" and the master profile says "AKS", say "AKS (Kubernetes)" or "Kubernetes" depending on context.
- It does not exceed 2 lines (about 25 words).

### 5. Curate skills

Group skills semantically (Cloud & Infrastructure / Languages / Architecture / Data / AI-ML / DevOps / Leadership). Reorder so the JD-matched group leads. Within each group, lead with JD-mentioned skills.

Don't pad. If the JD asks for a skill the user doesn't have, do NOT add it. Lead with the closest adjacent skill and let the user decide whether to apply.

### 6. Length decisions

**Hard cap: 2 pages, no exceptions** (ATS convention, not user preference). If the resume runs long, cut bullets — never spill to a third page. Post-render, `scripts/verify_output.py` renders to PDF and fails the build at page_count > 2.

**Choice of 1 vs. 2 pages within the cap is user-defined.** Read `master_profile.md` → Tailoring Rules. If silent, ask the user, then offer to record the answer.

**Trim order when overflowing the cap is user-defined.** Read `master_profile.md` → Tailoring Rules for the user's preferred trim order (typically: lowest-priority included employer's lowest-impact bullets first). If silent, ask the user before trimming and offer to record the answer.

### 7. Flag gaps in the tailoring notes

Always write a `tailoring_notes.md` file alongside the resume. Include:
- Headline chosen and why.
- Top 3 themes emphasized.
- Skills/requirements in the JD that the user doesn't have, and how the resume frames the gap.
- Any items from `master_profile.md` → Flags that came close to being used and were swapped.
- Whether the user should apply (your honest read) — but always frame this as the user's call, not yours.

## JD archetype mappings

If the user's `master_profile.md` → **Tailoring Rules** section documents JD-archetype-to-emphasis mappings (e.g., "FinTech roles → lead with X experience, emphasize Y, de-emphasize Z"), follow them as authoritative. If not, derive the emphasis order from the JD's must-haves + the user's strongest matching experience.
