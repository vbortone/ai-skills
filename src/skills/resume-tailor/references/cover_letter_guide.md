# Cover Letter Guide

Most cover letters are throw-away. The ones that get read are short, specific, and lead with why the candidate is uniquely positioned for *this* role *at this company*.

## Structure

**Hard cap: 1 page. 2-3 paragraphs total. ~200-250 words is the sweet spot; never exceed 280.** Letterhead + date + recipient block + salutation + signoff + name eat ~3 inches of vertical space before any body text starts, so body content gets less than half a page. If a paragraph is running long, cut a sentence rather than spilling onto a second page. Anonymize the client per the master profile's Anonymization Rule (PwC -> "Big 4 Accounting Firm" / "the client").

**Verification:** the build script renders the cover letter to PDF; if the rendered PDF is more than 1 page, trim the longest paragraph by one sentence and regenerate. Don't ship a cover letter where the signature spills onto page 2.

Use **2 paragraphs** when:
- The hook and experience can be tightly fused (e.g., the JD asks for one specific thing Vincent obviously has).
- The role is a startup / direct-to-founder application where brevity wins.

Use **3 paragraphs** (default) when there's a non-trivial differentiator or gap to address.

### Paragraph 1 - Hook + opening credibility (3-4 sentences)

State:
1. The exact role being applied to.
2. Vincent's strongest credibility signal for this role - current title, employer, and the closest-fit anchor (e.g., "25+ years architecting and modernizing enterprise platforms across financial services").
3. A specific reason this *company* is interesting - not boilerplate. Pull one signal from the JD or company's recent news / website / LinkedIn (a product, a stated value, a recent announcement) and tie it to Vincent's track record.

### Paragraph 2 - Track record tied to JD priorities + differentiator (4-6 sentences)

Pick 2-3 experiences from the master profile that map directly to the JD's top priorities, each with quantified impact (number, scale, outcome) and the technology / methodology / domain. Then close the paragraph with the single differentiator most relevant to this role:
- Legal background + technical fluency (good for legal-tech, regulatory, governance-heavy roles)
- MS FinTech (3.9 GPA) (good for fintech, capital markets, quant-adjacent roles)
- AI-assisted engineering certifications + production AI work (good for AI-leadership, modernization roles)
- 25+ year track record of cost-out and modernization wins (good for transformation roles)

Don't list all differentiators - pick the one most relevant. Use specific company / project names (`Wachtell, Lipton, Rosen & Katz`, `J.P. Morgan` for FinTech context) - recruiters read these and recognize the level of operating environment. Reference J.P. Morgan when the role is FinTech / capital markets even though it's omitted from the resume itself.

### Paragraph 3 - Honest gap (if any) + close (2-3 sentences)

If the JD has a domain or skill Vincent doesn't have hands-on, address it directly in one sentence - candor builds trust, especially for senior roles. Then close with one sentence inviting a conversation. Sign off with `Sincerely,` then the name.

If there's no meaningful gap to flag, this paragraph collapses into a single closing sentence and you're at 2 paragraphs total.

## Tone

Match the JD's tone:
- **Conservative corporate / Big 4 / regulated** - formal, measured, light on first-person superlatives.
- **Modern tech company** - confident but not boastful, slightly less formal.
- **Startup** - direct, results-forward, mention of velocity / ownership.

Default to "warm and confident" - never breathless, never grovelling.

## What to avoid

- "I'm passionate about" / "rockstar" / "ninja" / "10x" / "synergy" - clichés.
- Restating the JD back at them - they wrote it.
- Reciting the entire resume - the resume already does that.
- Generic openings: "I am writing to apply for the position of..." - replace with a real hook.
- Salutation guesses - use `Hiring Manager` if no name is in the JD; use the name if it is.

## Letterhead

Top of page:
```
Vincent Bortone
8349 NW 7th Pl, Plantation, FL 33317
561-343-0765 · vbortone@gmail.com · linkedin.com/in/vincentbortone

{Date in long form: May 6, 2026}

Hiring Manager *(or specific name if known)*
{Company}
{Company Address if available}
```

Then: `Dear Hiring Manager,` (or `Dear {Last Name},`).

Sign off: `Sincerely,` then `Vincent Bortone`.

## File output

Save as `{Company}_{Position}_{YYYY-MM-DD}_CoverLetter.docx` in the per-application subfolder. Use the same Calibri 11pt body, no fancy fonts, no graphics - same ATS rules as the resume.
