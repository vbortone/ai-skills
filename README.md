# ai-skills

Personal AI skills, packaged as one plugin (`ai-skills`) that installs in Claude Code, Cursor,
OpenAI Codex, and other tools that follow the [Agent Skills](https://agentskills.io/specification)
and [Agent Plugins](https://agent-plugins.org/specification) standards.

| Skill | What it does |
|-------|--------------|
| `resume-tailor` | Tailors a resume, cover letter, and recruiter pitch to one job description (ATS-safe DOCX). |
| `application-tracker` | Tracks applications, recruiter threads, prior outcomes, and someday tasks; archives finished applications. |
| `career-historian` | Interviews you to build a per-employer dossier of projects, skills evidence, and references. |
| `renaming-file-personal-style` | Renames household paperwork to `{Date}_{Recipient}_{Sender}_{Topic}.{ext}` using TypeSafe's Jev model. |

The skills hold no personal data. Each one reads your own files (profile, config, applications)
from a working folder you point it at; see `skills/<name>/examples/working-folder/` for templates.

## Install

### Claude Code

```
/plugin marketplace add vbortone/ai-skills
/plugin install ai-skills@vbortone-ai-skills
```

Or from a shell:

```bash
claude plugin marketplace add vbortone/ai-skills
```

```bash
claude plugin install ai-skills@vbortone-ai-skills
```

Skills are namespaced by the plugin: `/ai-skills:resume-tailor`, `/ai-skills:career-historian`, and so on.
Claude also picks them up automatically from their descriptions.

### Cursor

Add this repository as a plugin marketplace in Cursor's plugin settings
(`https://github.com/vbortone/ai-skills`), then install `ai-skills`. Cursor reads
`.cursor-plugin/marketplace.json` and `.cursor-plugin/plugin.json`.

### OpenAI Codex

```bash
codex plugin marketplace add vbortone/ai-skills
```

Then install `ai-skills` from the `/plugins` menu. Codex reads `.agents/plugins/marketplace.json`
and the root `plugin.json`.

### Any Agent Skills tool

Copy or symlink a folder from `skills/` into the tool's skills directory
(for example `~/.claude/skills/`). Each skill folder is self-contained, except that
`resume-tailor` calls scripts in the sibling `application-tracker` folder, so copy both.

## Python dependencies

Skills with helper scripts ship a `requirements.txt` in their folder:

```bash
pip install -r skills/resume-tailor/requirements.txt
```

```bash
pip install -r skills/renaming-file-personal-style/requirements.txt
```

## Layout

```
.claude-plugin/plugin.json         Claude Code plugin manifest
.claude-plugin/marketplace.json    Claude Code marketplace (this repo is its only plugin)
.cursor-plugin/plugin.json         Cursor plugin manifest
.cursor-plugin/marketplace.json    Cursor marketplace
.agents/plugins/marketplace.json   Codex marketplace
plugin.json                        Agent Plugins standard manifest (Codex portable layout)
skills/<name>/SKILL.md             the skills
tests/                             script tests (not loaded by any tool)
tools/check_manifests.py           keeps the manifests and skills consistent
```

## Development

When you change the plugin's name, version, or description, update all three plugin manifests,
then run the checks:

```bash
python tools/check_manifests.py
```

```bash
claude plugin validate .
```

## License

MIT
