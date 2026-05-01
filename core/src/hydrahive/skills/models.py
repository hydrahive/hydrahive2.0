from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

import yaml

SkillScope = Literal["system", "user", "agent"]

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


@dataclass
class Skill:
    name: str
    description: str
    when_to_use: str
    body: str
    scope: SkillScope
    owner: str  # username für user-scope, agent_id für agent-scope, "system" für system
    tools_required: list[str] = field(default_factory=list)


def is_valid_name(name: str) -> bool:
    return bool(NAME_RE.match(name))


def parse(text: str, *, scope: SkillScope, owner: str, fallback_name: str = "") -> Skill:
    """Parst eine Skill-Markdown-Datei mit YAML-Frontmatter."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return Skill(
            name=fallback_name, description="", when_to_use="", body=text.strip(),
            scope=scope, owner=owner,
        )
    front_raw, body = m.group(1), m.group(2)
    try:
        front = yaml.safe_load(front_raw) or {}
    except yaml.YAMLError:
        front = {}
    return Skill(
        name=str(front.get("name") or fallback_name),
        description=str(front.get("description") or ""),
        when_to_use=str(front.get("when_to_use") or ""),
        tools_required=list(front.get("tools_required") or []),
        body=body.strip(),
        scope=scope,
        owner=owner,
    )


def serialize(skill: Skill) -> str:
    """Skill als Markdown mit YAML-Frontmatter rendern."""
    front: dict = {
        "name": skill.name,
        "description": skill.description,
        "when_to_use": skill.when_to_use,
    }
    if skill.tools_required:
        front["tools_required"] = list(skill.tools_required)
    front_yaml = yaml.safe_dump(front, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{front_yaml}\n---\n\n{skill.body.strip()}\n"
