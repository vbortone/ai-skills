# Working folder template

The `resume-tailor` skill is methodology + tooling only. Personal data — your career, your headline preferences, your anonymization rules — lives in a **working folder** outside the skill. This directory is a template; copy it somewhere persistent on your machine and fill it in.

## Quickstart

1. Copy this directory to a stable location, e.g. `~/Documents/Job Search/`.
2. Rename `master_profile.md.example` → `master_profile.md` and fill in your career, education, certifications, headline candidates, and tailoring rules. The template marks every placeholder with `{braces}`.
3. Rename `tailor_config.json.example` → `tailor_config.json` and update the anonymization patterns to match your situation (or delete the `anonymization` section entirely if you don't need to anonymize anything).
4. From inside that folder, invoke the skill — e.g. "tailor a resume for this JD: …" — and it will write generated outputs into `Applications/{Company}_{Role}_{YYYY-MM-DD}/` siblings to your `master_profile.md`.

You do not need to fork this repo. The skill reads your working folder at runtime.

## File reference

### `master_profile.md`

Your single source of truth. The skill reads it on every run, never modifies it without your approval (see the Refresh workflow in `SKILL.md`), and treats anything not in this file as not real.

Sections you must fill in:

- **Identity** — headline candidates, contact, one-sentence intro.
- **Anonymization Rule** — prose description of which employer names get rewritten and to what. The code-level enforcement lives in `tailor_config.json`; this section explains *why* to the LLM doing the tailoring.
- **Work history** — every role you've ever held, with bullets exhaustive enough that the tailor can select a relevant subset per JD.
- **Education / Certifications / Skills inventory** — flat lists; the tailor reorders per JD.
- **Tailoring Rules** — your personal tactical guidance (always-include employers, default-off employers, headline-to-archetype mapping, length defaults). This is where you encode rules like "always include my current employer and the previous senior role; default-off the older / less-relevant roles unless I explicitly ask for them" specific to *your* career.
- **Flags & Items to Confirm Before Use** — content that requires careful framing or must be excluded entirely. The skill re-reads this before every generation.
- **Refresh Log** — append-only history of profile updates.

### `tailor_config.json`

Drives the post-render verifier (`scripts/verify_output.py`). Only code-level configuration belongs here; everything prose-shaped lives in `master_profile.md`.

#### Schema

```jsonc
{
  "anonymization": {
    // List of tokens that must never appear in a rendered resume / cover letter
    // / recruiter pitch. The verifier reads each pattern as a Python regex
    // (case-insensitive) and checks every paragraph, table cell, and
    // header/footer of the DOCX. Any match fails the build with exit code 1.
    "forbidden_tokens": [
      {
        // Human-readable label shown in the error message.
        "label": "Acme Corp",
        // Python regex. Use \\b for word boundaries to avoid false matches
        // inside other words. JSON requires double-escaping backslashes.
        "pattern": "\\bacme\\s+corp\\b"
      }
    ],
    // Optional. List of regex patterns describing target employers for which
    // the anonymization check should be skipped (because they ARE the target
    // employer and naming them is correct). The skill workflow consults this
    // list before deciding whether to pass --skip-anonymization to the build
    // scripts.
    "skip_when_target_employer_matches": [
      "\\bacme\\b"
    ]
  }
}
```

If you delete the `anonymization` section (or the whole file), the verifier logs an info note and skips the anonymization check entirely. The page-count check (resume ≤ 2 pages, cover letter ≤ 1 page) runs unconditionally.

## What lives where

| Concern | Lives in |
| --- | --- |
| Your career, headlines, tailoring rules, flags | `master_profile.md` |
| Anonymization regex patterns | `tailor_config.json` |
| Generated outputs | `Applications/{Company}_{Role}_{YYYY-MM-DD}/` |
| The skill's methodology (how to tailor, ATS rules, cover-letter structure) | The skill folder, not here |
| The DOCX build scripts and post-render verifier | The skill folder, not here |

If you find yourself wanting to edit the skill folder to bake in personal preferences, push the preference into `master_profile.md`'s "Tailoring Rules" section instead — that way your customization survives a skill upgrade.
