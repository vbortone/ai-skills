# Tailoring Notes Template

Use this structure verbatim when writing `tailoring_notes.md` for any application. It's derived from the highest-quality tailoring notes the skill has produced; deviating without reason produces notes that are harder for the user to scan later and harder for the skill itself to mine when a future tailoring run hits the same company.

Render the file as Markdown with the headings exactly as shown. Sections without content for a given application can be omitted, but section order should not change.

---

```markdown
# Tailoring Notes - {Company} {Role}

**Application date:** {YYYY-MM-DD}
**Source profile freshness:** master_profile.md last_refreshed {YYYY-MM-DD}{ — note any mid-tailoring corrections}

## Comp posture

{above target / at target / below target / not disclosed}. {One line on what the JD discloses and what the user's documented target is for this tier.}{ If below target, note explicitly that the user was prompted before generation and confirmed proceeding.}

## Project context

> Populate from application-tracker scripts in Step 0.

### Prior outcomes

{If find_prior_applications.py returned matches: quote the outcome excerpt(s) verbatim and call out what to do differently this time. Omit the section if no prior applications.}

### Recruiter context

{If find_recruiter_threads.py returned matches: list recruiter name, firm, last contact, comp anchor, current status. Omit the section if no thread.}

### Items to consider

{If find_someday_matches.py returned matches: list the Someday items the JD's domain could advance. Omit the section if no matches.}

## Role at a glance

- **Company:** {one-line description of what they do}
- **Title:** {full title}
- **Reports to:** {role}
- **Location:** {remote / hybrid / on-site + city}
- **Mission:** {2-4 sentence summary of what the role exists to do, scope, team size, key constraints}

## Tailoring choices

### Headline chosen

**"{Headline from master_profile.md Headline Inventory}"** — {one-sentence rationale tying the chosen headline to the JD's title and seniority. Mention any headline candidates that were considered and rejected, and why.}

### Top 3 themes emphasized

1. **{Theme 1, named in the JD's own language}.** {Which specific bullets from master_profile.md were selected for this theme and what JD signals they map to.}
2. **{Theme 2}.** {Same shape — which bullets, which JD signals.}
3. **{Theme 3}.** {Same.}

### What was de-emphasized / cut

- **{Item}** — {one-line reason: anonymization, length, off-by-default rule, etc.}
- **{Item}** — {one-line reason}
- **{Item}** — {one-line reason}

### JD requirements vs. profile — honest read

| JD asks for | User has | Notes |
| --- | --- | --- |
| {requirement 1} | {best matching evidence from master_profile.md} | {strong / match / adjacent / gap} |
| {requirement 2} | {evidence} | {assessment} |
| {requirement 3} | {evidence} | {assessment} |
| **{Helpful-but-not-required item}** | {evidence or "—"} | {gap / covered / adjacent} |

Lead with the must-haves; "helpful, not required" items can be bolded for visibility. Be honest about gaps — soft language ("strong overshoot", "adjacent rather than direct", "match") tells the user what they're walking into.

### Mid-tailoring corrections

{If anything in master_profile.md was updated during this run — e.g. a stack item the user remembered partway through, a date correction — list the changes here with file references. Omit if no corrections were applied.}

### Items from the Flags section that came close

- **{Flag item}** — INCLUDED with {approved framing} / NOT included because {reason}.
- **{Flag item}** — {same shape}.

### Client anonymization

- {One line on which anonymized employer / project / product names appeared in the source bullets, and how each was rewritten on the output.}
- {Note any items that were kept on the resume because their internal name is generic-sounding enough not to expose the underlying employer.}

## My honest read

{2-4 paragraphs of independent assessment. Cover:
- Whether the user should apply — but frame this as the user's call, not yours.
- Where the strongest fit is and where the genuine gaps are.
- Any signal in the JD that suggests the role is closer to / further from what the user actually wants than the title implies.
- Whether the recruiter pitch's phone-screen variant fits this conversation if a call gets booked.

This section is for the user's eyes only — be direct. Hedging here defeats the purpose of the notes.}
```

---

## Section ordering rationale

- **Comp posture goes first** because it's the single most decision-relevant fact. If the JD is below target, the user sees that before scrolling past the rest.
- **Project context next** because re-applications, recruiter threads, and Someday matches change how the rest of the package reads. Putting them above tailoring choices lets the user evaluate the tailoring decisions in light of what the skill already knew.
- **Role at a glance** anchors the rest of the document — what's the user looking at.
- **Tailoring choices** is the bulk: headline, themes, cuts, JD-vs-profile table, mid-corrections, flag-handling, anonymization.
- **My honest read** at the bottom — the recommendation lives after the evidence that supports it.
