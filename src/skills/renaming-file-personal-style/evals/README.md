# Evals: renaming-file-personal-style

Six evals in `evals.json` (skill-creator format) cover the behaviors the skill promises:

| id | name | What it checks |
|----|------|----------------|
| 1 | bank-statement-ignores-birthday | Statement date beats period/due dates; an `ignore_dates` birthday is never offered |
| 2 | irs-notice-to-household | Document addressed to two people picks the shared recipient |
| 3 | shouted-utility-letterhead | ALL-CAPS sender is title-cased and its corporate suffix stripped |
| 4 | undated-receipt-falls-back-to-file-date | No date in the text, so the file's creation date is used |
| 5 | batch-with-existing-name-collision | One batch run; the colliding name gets `_2` and the existing file is untouched |
| 6 | missing-api-key-no-llm-fallback | No `TYPESAFE_API_KEY`: exit 2, nothing renamed, no names guessed by the agent |

Fixtures in `files/` use the placeholder household (Alex, Sam, Household) from
`files/renamer_config.json`. No real personal data belongs here.

Each eval has two kinds of assertions:

- `checks`: machine-graded against the inbox folder after a run, by `check_renames.py`
  (files present or absent by regex, a file left unchanged, the creation-date fallback).
- `expectations`: plain-English statements a grader agent judges from the transcript, such as
  "ran classify.py rather than classifying the document itself".

## Running

Install deps first (`pip install -r ../requirements.txt`).

**Offline (no API key, deterministic):** unit checks on date and sender candidate finding and
sender normalization, then evals 1–5 run through the full pipeline with a stub that answers like
a correct Jev. This catches regressions in code and graders but says nothing about Jev's judgment.

```bash
python evals/run_evals.py --mode offline
```

**Live, script level (real Jev):** runs the real `classify.py` CLI against TypeSafe, applies the
proposals, and grades. Evals without a key are skipped; eval 6 always runs with the key unset.

```bash
python evals/run_evals.py --mode live [--eval-id 3] [--keep ./eval-inboxes]
```

Both print one JSON report and exit 0 only if every check passed. Each proposal includes the
per-token probabilities, which helps tune `review_confidence`.

**Agent level (Claude following SKILL.md):** use the skill-creator workflow. Spawn one subagent
per eval with the skill path and the eval's prompt, copying the eval's `files` into a fresh
inbox folder, and unsetting any `env.unset` variables for that run. Results go in
`renaming-file-personal-style-workspace/iteration-N/` (gitignored). Then grade the inbox with:

```bash
python evals/check_renames.py --eval-id <N> --dir <inbox after the run>
```

The output uses the `grading.json` shape (`text`, `passed`, `evidence`). Have a grader agent judge
`expectations` against the transcript and add those results to the same file.
