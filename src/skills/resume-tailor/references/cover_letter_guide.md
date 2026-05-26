# Cover Letter Guide

Most cover letters are throw-away. The ones that get read are short, specific, and lead with why the candidate is uniquely positioned for *this* role *at this company*.

## Structure

**Hard cap: 1 page. 2-3 paragraphs total. ~200-250 words is the sweet spot; never exceed 280.** Letterhead + date + recipient block + salutation + signoff + name eat ~3 inches of vertical space before any body text starts, so body content gets less than half a page. If a paragraph is running long, cut a sentence rather than spilling onto a second page. Anonymize per the user's Anonymization Rule (documented in `master_profile.md`, enforced by `tailor_config.json`).

**Verification:** `scripts/build_cover_letter_docx.py` renders the cover letter to PDF via `scripts/verify_output.py` and fails (exit code 2) if the rendered PDF is more than 1 page — trim the longest paragraph by one sentence and regenerate. Don't ship a cover letter where the signature spills onto page 2.

Use **2 paragraphs** when:
- The hook and experience can be tightly fused (e.g., the JD asks for one specific thing the user obviously has).
- The role is a startup / direct-to-founder application where brevity wins.

Use **3 paragraphs** (default) when there's a non-trivial differentiator or gap to address.

### Paragraph 1 - Hook + opening credibility (3-4 sentences)

State:
1. The exact role being applied to.
2. The user's strongest credibility signal for this role — current title, employer, and the closest-fit anchor (e.g., "25+ years architecting and modernizing enterprise platforms across financial services").
3. A specific reason this *company* is interesting — not boilerplate. Pull one signal from the JD or company's recent news / website / LinkedIn (a product, a stated value, a recent announcement) and tie it to the user's track record.

### Paragraph 2 - Track record tied to JD priorities + differentiator (4-6 sentences)

Pick 2-3 experiences from `master_profile.md` that map directly to the JD's top priorities, each with quantified impact (number, scale, outcome) and the technology / methodology / domain. Then close the paragraph with the single differentiator most relevant to this role. The user's `master_profile.md` → Tailoring Rules section may enumerate differentiators with JD-archetype mappings — follow them when present.

Don't list all differentiators — pick the one most relevant. Specific company / project names recruiters recognize (large-name employers, well-known products) often signal the level of operating environment; use them when truthful. The cover letter MAY surface employer names that are default-off on the resume itself, when the JD's domain calls for that context.

### Paragraph 3 - Honest gap (if any) + close (2-3 sentences)

If the JD has a domain or skill the user doesn't have hands-on, address it directly in one sentence — candor builds trust, especially for senior roles. Then close with one sentence inviting a conversation. Sign off with `Sincerely,` then the user's name.

If there's no meaningful gap to flag, this paragraph collapses into a single closing sentence and you're at 2 paragraphs total.

## Tone

Match the JD's tone:
- **Conservative corporate / regulated** — formal, measured, light on first-person superlatives.
- **Modern tech company** — confident but not boastful, slightly less formal.
- **Startup** — direct, results-forward, mention of velocity / ownership.

Default to "warm and confident" — never breathless, never grovelling.

## What to avoid

- "I'm passionate about" / "rockstar" / "ninja" / "10x" / "synergy" — clichés.
- Restating the JD back at them — they wrote it.
- Reciting the entire resume — the resume already does that.
- Generic openings: "I am writing to apply for the position of..." — replace with a real hook.
- Salutation guesses — use `Hiring Manager` if no name is in the JD; use the name if it is.

## Letterhead

Top of page:
```
{User's Name}
{Street Address, City, State Zip}
{Phone} · {Email} · {LinkedIn URL}

{Date in long form: May 6, 2026}

Hiring Manager *(or specific name if known)*
{Company}
{Company Address if available}
```

Then: `Dear Hiring Manager,` (or `Dear {Last Name},`).

Sign off: `Sincerely,` then the user's name.

All identity fields come from `master_profile.md` → Identity.

## File output

Save as `{Company}_{Position}_{YYYY-MM-DD}_CoverLetter.docx` in the per-application subfolder. Use the same Calibri 11pt body, no fancy fonts, no graphics — same ATS rules as the resume.
