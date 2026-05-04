from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal

import yaml

logger = logging.getLogger(__name__)

SkillScope = Literal["system", "user", "agent"]

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


@dataclass
class SkillSource:
    """Externe Quelle die zum Skill gehört (Forum, API, Doku). Beim load_skill
    werden die URLs als Hinweis im Body angehängt — der Agent kann sie via
    fetch_url() abrufen, Auth wird automatisch via Credential-Profile-Match
    eingehängt (oder explizit per `auth=<profilname>`)."""
    url: str
    auth: str = ""
    description: str = ""


@dataclass
class Skill:
    name: str
    description: str
    when_to_use: str
    body: str
    scope: SkillScope
    owner: str
    tools_required: list[str] = field(default_factory=list)
    sources: list[SkillSource] = field(default_factory=list)


def is_valid_name(name: str) -> bool:
    return bool(NAME_RE.match(name))


def _parse_sources(raw) -> list[SkillSource]:
    if not raw:
        return []
    out: list[SkillSource] = []
    for s in raw:
        if isinstance(s, dict):
            out.append(SkillSource(
                url=str(s.get("url") or ""),
                auth=str(s.get("auth") or ""),
                description=str(s.get("description") or ""),
            ))
        elif isinstance(s, str):
            out.append(SkillSource(url=s))
    return [s for s in out if s.url]


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
    except yaml.YAMLError as e:
        logger.warning("Skill-Frontmatter ungültig (%s) — fallback auf Defaults: %s", fallback_name, e)
        front = {}
    return Skill(
        name=str(front.get("name") or fallback_name),
        description=str(front.get("description") or ""),
        when_to_use=str(front.get("when_to_use") or ""),
        tools_required=list(front.get("tools_required") or []),
        sources=_parse_sources(front.get("sources")),
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
    if skill.sources:
        front["sources"] = [
            {"url": s.url, **({"auth": s.auth} if s.auth else {}),
             **({"description": s.description} if s.description else {})}
            for s in skill.sources
        ]
    front_yaml = yaml.safe_dump(front, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{front_yaml}\n---\n\n{skill.body.strip()}\n"
