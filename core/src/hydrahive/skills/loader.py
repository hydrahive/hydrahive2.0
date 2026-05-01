"""Skill-CRUD über Filesystem. Idempotent, kein Lock — gleichzeitige Saves
an dieselbe Datei wären unwahrscheinlich (User-Editor)."""
from __future__ import annotations

import logging
from pathlib import Path

from hydrahive.skills._paths import agent_dir, dir_for, file_for, system_dir, user_dir
from hydrahive.skills.models import Skill, SkillScope, is_valid_name, parse, serialize

logger = logging.getLogger(__name__)


def _list_dir(d: Path, scope: SkillScope, owner: str) -> list[Skill]:
    if not d.exists():
        return []
    out: list[Skill] = []
    for f in sorted(d.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("skill nicht lesbar %s: %s", f, e)
            continue
        skill = parse(text, scope=scope, owner=owner, fallback_name=f.stem)
        if not skill.name:
            skill.name = f.stem
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
