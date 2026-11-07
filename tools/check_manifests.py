"""Check that the plugin manifests and skills agree with each other.

The repo ships one plugin described by several manifests, one per tool:
  plugin.json                        Agent Plugins standard (Codex portable layout)
  .claude-plugin/plugin.json         Claude Code
  .cursor-plugin/plugin.json         Cursor
  .claude-plugin/marketplace.json    Claude Code marketplace
  .cursor-plugin/marketplace.json    Cursor marketplace
  .agents/plugins/marketplace.json   Codex marketplace

The plugin manifests must share name, version and description, every marketplace must
list the plugin by that name, and every skills/<dir>/SKILL.md must meet the Agent Skills
spec (name matches dir, lowercase-hyphen, <= 64 chars; description 1-1024 chars).

Usage: python tools/check_manifests.py [--root PATH]
Prints one JSON object on stdout. Exit 0 = consistent, 1 = problems found.
"""

import argparse
import json
import re
import sys
from pathlib import Path

PLUGIN_MANIFESTS = ["plugin.json", ".claude-plugin/plugin.json", ".cursor-plugin/plugin.json"]
MARKETPLACES = [
    ".claude-plugin/marketplace.json",
    ".cursor-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
]
SHARED_KEYS = ["name", "version", "description"]
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def load(root: Path, rel: str, problems: list):
    path = root / rel
    if not path.is_file():
        problems.append(f"{rel}: missing")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        problems.append(f"{rel}: invalid JSON ({e})")
        return None


def frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    block = text.split("---", 2)[1]
    out = {}
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=Path(__file__).resolve().parent.parent, type=Path)
    root = ap.parse_args().root
    problems: list = []

    manifests = {rel: load(root, rel, problems) for rel in PLUGIN_MANIFESTS}
    reference = manifests[PLUGIN_MANIFESTS[0]] or {}
    for rel, data in manifests.items():
        if data is None:
            continue
        for key in SHARED_KEYS:
            if data.get(key) != reference.get(key):
                problems.append(f"{rel}: {key} differs from {PLUGIN_MANIFESTS[0]}")

    plugin_name = reference.get("name")
    for rel in MARKETPLACES:
        data = load(root, rel, problems)
        if data is None:
            continue
        names = [p.get("name") for p in data.get("plugins", [])]
        if plugin_name not in names:
            problems.append(f"{rel}: does not list plugin '{plugin_name}'")

    skills = []
    for skill_dir in sorted(p for p in (root / "skills").iterdir() if p.is_dir()):
        # Exact-case check: Windows and macOS file systems would accept skill.md here.
        if "SKILL.md" not in {p.name for p in skill_dir.iterdir()}:
            problems.append(f"skills/{skill_dir.name}: no SKILL.md (exact case)")
            continue
        fm = frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
        name, desc = fm.get("name", ""), fm.get("description", "")
        if name != skill_dir.name:
            problems.append(f"skills/{skill_dir.name}: name '{name}' does not match folder")
        if not NAME_RE.match(name) or len(name) > 64:
            problems.append(f"skills/{skill_dir.name}: name not lowercase-hyphen <= 64 chars")
        if not 1 <= len(desc) <= 1024:
            problems.append(f"skills/{skill_dir.name}: description is {len(desc)} chars (1-1024)")
        skills.append(skill_dir.name)

    print(json.dumps({"ok": not problems, "plugin": plugin_name,
                      "version": reference.get("version"), "skills": skills,
                      "problems": problems}, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
