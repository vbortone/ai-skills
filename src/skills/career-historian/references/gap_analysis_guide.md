# Gap-Analysis Guide

How to review a dossier and generate the follow-up questions a good biographer would ask. Used in SKILL.md Step 4 — either by a spawned subagent (preferred: fresh eyes, no interview momentum) or by the interviewer in a deliberate review pass.

## Why this pass exists

During a live loop the interviewer optimizes for flow — short probes, fast capture, respect for the user's energy. That necessarily leaves holes. This pass reads the dossier cold and asks: *if a resume-tailoring run hit this dossier tomorrow, what would it wish were here?* The output is questions, not edits — the user supplies the facts.

## Gap categories

Scan every dossier section against each category. Cite the specific dossier line a question targets, so the question can say "you mentioned X — …" instead of asking generically.

1. **Unquantified outcomes.** A project with a result but no number ("improved performance", "reduced costs"). Ask for the metric, the baseline, or at least a bounded estimate.
2. **Projects without outcomes.** Action described, result absent. "What changed because this shipped?"
3. **Missing role isolation.** "We built…" with no statement of what the user specifically owned.
4. **Skills without evidence.** A skills-table row with no project or anecdote anchoring it. Either link it to a captured project or ask where it was exercised.
5. **Date gaps and vagueness.** Missing start/end months, projects that can't be placed in the tenure, gaps between projects longer than ~6 months (there may be an entire uncaptured project in there).
6. **Contacts without relationship context.** A name with no "worked together on" or no reference-potential call. These are the fields that make a contact usable years later.
7. **Scale, leadership, and budget angles.** JDs ask for team sizes, budget ownership, org scope. If the tenure plausibly involved any (a senior title, a long tenure, a big project) and the dossier is silent, ask.
8. **Incomplete stories.** STAR fragments — a situation with no resolution, a result with no setup. Behavioral-interview prep needs whole stories.
9. **Era-defining context missing.** No "engagement context" — why the company hired them, what era of the company it was (pre-IPO scramble? post-acquisition integration?). One sentence of context makes every bullet beneath it legible.
10. **Cross-dossier echoes.** A skill or contact mentioned here that another dossier covers more thinly — flag the *other* dossier's open question, not this one's.

## Output format

Return a prioritized list, highest-value first. For each question:

```json
{
  "questions": [
    {
      "priority": 1,
      "category": "unquantified-outcomes",
      "target": "Projects > Payment gateway migration",
      "question": "You said the migration 'cut checkout failures significantly' — roughly what failure rate before and after, even ballpark?",
      "why_it_matters": "This is the dossier's strongest bullet candidate; a number makes it resume-grade."
    }
  ]
}
```

Priority guidance: rank by resume value, not by category order — a missing number on the tenure's flagship project outranks a missing month on a side project. 8–15 questions is a healthy yield for a mid-sized dossier; if you found 30, return the best 15.

## What happens to the output

The interviewer asks the top 3–5 immediately (one at a time, normal loop etiquette), then appends the remainder to the dossier's **Open questions** section as unchecked boxes with today's date:

```markdown
- [ ] (2026-06-09) You mentioned mentoring two juniors — did either get promoted during your tenure?
```

Open questions are the next session's agenda; `dossier_status.py` counts the unchecked ones so Step 1's coverage map can surface stale or question-heavy dossiers.
