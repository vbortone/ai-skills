# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal AI Skills library — reusable Claude Code skills + agent implementations. Skills are **user-agnostic**: they define folder structures, processes, and tooling, but never bake in any single user's personal data.

## Repository Structure

- `src/agents/` — AI agent implementations
- `src/skills/` — Reusable Claude Code skills
  - `resume-tailor/` — Tailor a resume, cover letter, and recruiter pitch against one JD. Reads the user's `master_profile.md` and `tailor_config.json` from their working folder. Outputs ATS-safe DOCX via `scripts/build_resume_docx.py` + `scripts/build_cover_letter_docx.py`; post-render verifier (`scripts/verify_output.py`) enforces anonymization rules and page-count caps. Freshness helper (`scripts/refresh_profile.py`) walks the working folder for files newer than the profile's `last_refreshed`.
  - `application-tracker/` — Track job-search state across applications, recruiter threads, prior outcomes, and the user's task list. Sibling to resume-tailor; resume-tailor's Step 0 invokes application-tracker's three read scripts (`find_prior_applications.py`, `find_recruiter_threads.py`, `find_someday_matches.py`) for context. Owns the only write script in the pair: `archive_application.py` (move active → archived, stub `_outcome.md`).
  - `renaming-file-personal-style/` — File renaming helper.

Each skill follows the same internal layout:

```
src/skills/<skill-name>/
├── SKILL.md              # methodology, process, workflow steps
├── references/           # generic guides referenced from SKILL.md
├── scripts/              # Python helpers, all emitting JSON on stdout
├── examples/             # bootstrap templates a new user copies
│   └── working-folder/
└── requirements.txt      # when the skill has Python deps
```

## User-agnostic design contract

When changing a skill, keep personal data **out of the skill folder**:

- The skill ships methodology, process, scripts, and `examples/working-folder/` bootstrap templates — never any user's career, employers, recruiters, or anonymization rules.
- The user's **working folder** (e.g. `~/Documents/Job Search/`) carries everything personal: `master_profile.md`, `tailor_config.json`, `Applications/`, `Archive/`, `memory/`, `TASKS.md`.
- Scripts accept explicit working-folder paths via CLI flags; they never assume a fixed location.
- When a skill needs a content decision (which employers to include, what bullet counts to use, page count by role tier, etc.), it consults the user's working-folder context — typically `master_profile.md → Tailoring Rules`. If no rule is documented, the skill **asks the user before proceeding** rather than guessing.
- If you find yourself wanting to add a default to the skill that affects what shows up on a user's output, push the default into the bootstrap template instead.

`examples/working-folder/` in each skill is the canonical reference for what a user's working folder should look like. Keep templates in sync with the conventions SKILL.md describes.

## Python tooling

Skills with Python scripts ship a `requirements.txt`:

- `src/skills/resume-tailor/requirements.txt` — `python-docx`, `docx2pdf` (requires MS Word on Windows), `pypdf`.

To work on those scripts locally:

```bash
uv venv .venv
source .venv/Scripts/activate   # bash on Windows; .venv/bin/activate on Unix
uv pip install -r src/skills/resume-tailor/requirements.txt
```

Scripts that produce structured output emit a single JSON object to stdout — keep that convention so SKILL.md workflows can parse the result. Errors go to stderr; exit codes are documented in each script's module docstring.

## Conventions

- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/#specification) for every commit. Scope each commit to one skill where possible: `feat(resume-tailor): ...`, `refactor(application-tracker): ...`, `docs(resume-tailor): ...`.
- Commit messages should explain **why**, not just what — these messages are the change log future Claude sessions read first.
- Smoke-test scripts against a `tempfile.TemporaryDirectory()` before merging changes that touch script behavior — there's no automated test suite yet.
- When a script is a write operation (e.g. `archive_application.py`), add a `--dry-run` flag and refuse to clobber existing destinations by default.

## Notes

No formal build / lint / test tooling is configured at the repo level. Per-skill Python scripts use ad-hoc smoke tests run against temp working folders during development. If formal tooling lands, update this file.
