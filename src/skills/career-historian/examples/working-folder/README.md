# Working folder template — career-historian

The `career-historian` skill is methodology + tooling only. Your employment history — projects, skills evidence, contacts — lives in dossiers at a **destination you choose**, and the skill's config lives in your working folder (the same folder resume-tailor and application-tracker use).

## Quickstart

1. Copy `historian_config.json.example` → `{working_folder}/historian_config.json` and pick a destination (see below). The default — a `career-history/` folder inside your working folder — is right for most users.
2. Optionally pre-create `career-history/` and copy `INDEX.md.example` → `career-history/INDEX.md`. The skill will create both on first run if you don't.
3. Invoke the skill — e.g. *"interview me about my time at {Company}"* or *"here's my old resume, add it to my career history"*. The skill creates dossiers from `company_dossier.md.example`'s structure as you go.

You do not need to fork the skill repo. The skill reads your working folder at runtime.

## Choosing a destination

### `local` (default)

```json
{
  "destination": {
    "type": "local",
    "path": "career-history"
  }
}
```

- A relative `path` resolves against your working folder.
- An absolute `path` is allowed — point it inside a notes vault on disk (e.g. an Obsidian vault folder) if you want dossiers living in your second brain while remaining plain files.

### `mcp`

```json
{
  "destination": {
    "type": "mcp",
    "server": "obsidian",
    "base_path": "Career/Job History",
    "notes": "One note per company under base_path; use the server's read/write/list note tools."
  }
}
```

- `server` — the MCP server name as connected in your client (the skill verifies it's reachable at session start and offers local fallback if not).
- `base_path` — folder/prefix inside that destination where one note per company goes.
- `notes` — free-text hints for the skill about how this server organizes content; optional.

With an `mcp` destination, the skill still maintains `{working_folder}/career-history/INDEX.md` locally — that's how the sibling resume-tailor skill's freshness check learns that new history exists.

## What lives where

| Concern | Lives in |
| --- | --- |
| Where dossiers go | `historian_config.json` |
| The dossiers themselves (projects, skills, contacts) | your configured destination |
| The per-company index resume-tailor's freshness check watches | `career-history/INDEX.md` (always local) |
| Your distilled, tailoring-ready career summary | `master_profile.md` (owned by resume-tailor; synced manually via its refresh flow) |
| Interview methodology, question banks, gap analysis | the skill folder, not here |

## File reference

- `historian_config.json.example` — destination config; copy and edit.
- `career-history/company_dossier.md.example` — the canonical dossier structure. The skill follows it so `dossier_status.py` can parse coverage; keep the level-2 section headings if you hand-edit dossiers.
- `career-history/INDEX.md.example` — the index file the skill maintains at session end.
