"""Skill-CRUD über Filesystem. Idempotent, kein Lock — gleichzeitige Saves
an dieselbe Datei wären unwahrscheinlich (User-Editor)."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from hydrahive.skills._paths import agent_dir, dir_for, file_for, system_dir, user_dir
from hydrahive.skills.models import Skill, SkillScope, is_valid_name, parse, serialize

logger = logging.getLogger(__name__)

_DEFAULTS_SRC = Path(__file__).parent / "system_defaults"


def install_system_defaults() -> None:
    """Kopiert die ausgelieferten Default-Skills nach $HH_DATA_DIR/skills/system/
    falls dort noch keine sind. Existierende werden nicht überschrieben —
    Admin-Edits bleiben erhalten."""
    target = system_dir()
    target.mkdir(parents=True, exist_ok=True)
    if not _DEFAULTS_SRC.exists():
        return
    for src in sorted(_DEFAULTS_SRC.glob("*.md")):
        dst = target / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
            logger.info("System-Skill installiert: %s", src.name)


def _collect_skill_files(d: Path) -> list[tuple[Path, str]]:
    """Liefert (path, fallback_name) für alle Skills im Verzeichnis.

    Unterstützte Layouts (werden kombiniert, Duplikate werden entfernt):
      skillname.md                         — flach (bisheriges Format)
      skillname/SKILL.md                   — einstufig (benithors/skills-Style)
      category/skillname/SKILL.md          — zweistufig (Orchestra Research-Style)

    Der fallback_name kommt aus dem direkten Elternverzeichnis der SKILL.md
    bzw. dem Stem der flachen .md-Datei.
    """
    seen: set[Path] = set()
    result: list[tuple[Path, str]] = []

    def _add(f: Path, name: str) -> None:
        if f not in seen:
            seen.add(f)
            result.append((f, name))

    for f in sorted(d.glob("*.md")):
        _add(f, f.stem)

    for pattern in ("*/SKILL.md", "*/skill.md", "*/*/SKILL.md", "*/*/skill.md"):
        for f in sorted(d.glob(pattern)):
            _add(f, f.parent.name)

    return result


def _list_dir(d: Path, scope: SkillScope, owner: str) -> list[Skill]:
    if not d.exists():
        return []
    out: list[Skill] = []
    for f, fallback in _collect_skill_files(d):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("skill nicht lesbar %s: %s", f, e)
            continue
        skill = parse(text, scope=scope, owner=owner, fallback_name=fallback)
        if not skill.name:
            skill.name = fallback
        out.append(skill)
    return out


def list_for_agent(agent_id: str, owner: str, *, disabled: list[str] | None = None) -> list[Skill]:
    """Merge system + user + agent. Bei Namens-Kollision: agent > user > system.
    `disabled` ist eine Liste von Skill-Namen die ausgeblendet werden sollen."""
    bag: dict[str, Skill] = {}
    for s in _list_dir(system_dir(), "system", "system"):
        bag[s.name] = s
    for s in _list_dir(user_dir(owner), "user", owner):
        bag[s.name] = s
    for s in _list_dir(agent_dir(agent_id), "agent", agent_id):
        bag[s.name] = s
    skip = set(disabled or [])
    return [s for n, s in sorted(bag.items()) if n not in skip]


def get_skill(scope: SkillScope, owner: str, name: str) -> Skill | None:
    if not is_valid_name(name):
        return None
    f = file_for(scope, owner, name)
    if not f.exists():
        return None
    return parse(f.read_text(encoding="utf-8"), scope=scope, owner=owner, fallback_name=name)


def save_skill(skill: Skill) -> tuple[bool, str]:
    if not is_valid_name(skill.name):
        return False, "skill_name_invalid"
    d = dir_for(skill.scope, skill.owner)
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{skill.name}.md"
    tmp = f.with_suffix(".md.tmp")
    tmp.write_text(serialize(skill), encoding="utf-8")
    tmp.replace(f)
    return True, ""


def delete_skill(scope: SkillScope, owner: str, name: str) -> bool:
    f = file_for(scope, owner, name)
    if not f.exists():
        return False
    f.unlink()
    return True
