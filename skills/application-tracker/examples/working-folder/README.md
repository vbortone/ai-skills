# Working folder template — application-tracker

The `application-tracker` skill reads context from your working folder and provides three lookup scripts (`find_prior_applications.py`, `find_recruiter_threads.py`, `find_someday_matches.py`). It does not modify your data.

This template documents the conventions the skill expects. You can override every path via CLI flags on the scripts if you organize things differently.

## Expected structure

```
{working_folder}/
├── master_profile.md             # owned by the resume-tailor skill
├── tailor_config.json            # owned by the resume-tailor skill
├── TASKS.md                      # task list — see TASKS.md.example
├── memory/
│   └── people/
│       └── recruiters.md         # recruiter threads — see recruiters.md.example
├── Applications/                 # active applications (resume-tailor writes these)
│   └── <Company>_<Role>_<YYYY-MM-DD>/
│       ├── ..._Resume.docx
│       ├── ..._CoverLetter.docx
│       ├── job_description.txt
│       └── tailoring_notes.md
└── Archive/
    └── Applications/             # closed-out applications
        └── <Company>_<Role>_<YYYY-MM-DD>/
            ├── ... (everything from the active folder)
            └── _outcome.md       # outcome + lessons — see _outcome.md.example
```

## Convention notes

- **Folder name format:** `{Company}_{Role}_{YYYY-MM-DD}`. The company segment is what `find_prior_applications.py` fuzzy-matches against. Spaces become underscores; punctuation is stripped. Re-applications to the same company+role+date can suffix `_v2`, `_v3`, etc.
- **`_outcome.md` is required** for entries in `Archive/Applications/`. The first paragraph of content is what `find_prior_applications.py` returns as the outcome excerpt, so lead with the outcome (one line) and the most important lesson (one or two sentences). Detailed analysis can follow.
- **`recruiters.md`** uses one Markdown section per active thread, with the heading as the recruiter's name + firm. The skill returns the full section as the excerpt; the LLM extracts structured fields from your prose. There is no enforced schema, but consistency helps — see `recruiters.md.example` for a working pattern.
- **`TASKS.md`** uses Markdown headings to delimit sections (`## Active`, `## Waiting On`, `## Someday`, `## Done`). `find_someday_matches.py` scans the `Someday` section by default — override with `--section-heading`.

## File reference

- `_outcome.md.example` — template for archived applications.
- `recruiters.md.example` — template recruiter thread file.
- `TASKS.md.example` — template task list with all four sections.
