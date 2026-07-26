"""Structural / spec-conformance checks for the bundled skills.

Guards the unified `mt-` prefix, hyphenated (spec-valid) names, and the
SKILL.md <-> folder <-> SKILL_NAMES consistency. No backend required.
"""
import re
from pathlib import Path

import pytest

from mobility_toolkit.installer import SKILL_NAMES, SKILLS_SRC

NAME_RE = re.compile(r"^mt-[a-z0-9-]+$")
EXPECTED = {
    "mt-translate", "mt-homology", "mt-classify", "mt-mobility",
    "mt-gsd", "mt-fusion", "mt-models", "mt-doctor", "mt-boundary",
    "mt-halfspace", "mt-cheshire",
}


def _frontmatter(text):
    """Minimal YAML-frontmatter reader (name/description only; no yaml dep)."""
    assert text.startswith("---"), "SKILL.md must start with a --- frontmatter block"
    block = text.split("---", 2)[1]
    out = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip().strip('"')
    return out


def test_skill_names_match_disk():
    on_disk = {p.name for p in SKILLS_SRC.iterdir() if p.is_dir()}
    assert on_disk == EXPECTED
    assert set(SKILL_NAMES) == EXPECTED
    assert len(SKILL_NAMES) == len(set(SKILL_NAMES)) == 11


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_skill_is_well_formed(name):
    folder = SKILLS_SRC / name
    skill_md = folder / "SKILL.md"
    assert skill_md.is_file(), f"{name} missing SKILL.md"

    fm = _frontmatter(skill_md.read_text(encoding="utf-8"))
    # spec-conformant, prefixed name that matches the folder
    assert NAME_RE.match(fm.get("name", "")), f"{name}: invalid skill name {fm.get('name')!r}"
    assert fm["name"] == name, f"{name}: frontmatter name != folder"
    # description should say *when* to use it (a matchable trigger phrase)
    desc = fm.get("description", "")
    assert len(desc) > 40, f"{name}: description too short"
    assert any(t in desc.lower() for t in ("use ", "when", "run this")), \
        f"{name}: description lacks a usage trigger"
    # the legacy non-standard `commands:` field must be gone
    assert "commands" not in fm, f"{name}: drop the non-standard commands: field"

    # exactly one runnable script, named after the skill
    scripts = list((folder / "scripts").glob("*.py"))
    assert len(scripts) == 1, f"{name}: expected one script, found {scripts}"
    assert scripts[0].name == f"{name}.py"
    # script imports the core (so the installer's path-bootstrap is what it needs)
    assert "import mobility_toolkit" in scripts[0].read_text(encoding="utf-8") or \
           "from mobility_toolkit" in scripts[0].read_text(encoding="utf-8")
