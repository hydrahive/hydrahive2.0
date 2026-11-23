"""Wann laufen Agenten-Befehle in der Sandbox? (Ziel agenten-projekt-isolation.md, Etappe B2a)

- Schalter ``HH_AGENT_SANDBOX`` (Umgebung des Dienstes): ``on`` = an. Standard **aus**, bis der Live-Test bestanden
  ist; danach wird der Standard umgedreht.
- Nur Agent-Typ ``project`` und ``specialist``. Buddy/Master bleibt draußen (Till 23.11.: „Buddy behält Vorrang“).
  Unbekannter Typ → Sandbox (fail-closed, wie _shell_guard).
- Nur mit Projekt-Workspace. Ohne Projekt (z. B. Spezialist ohne Projekt) arbeitet der Agent in seinem eigenen
  Agenten-Workspace; der wird dann zur Sandbox-Wurzel.
- Container-Projekte (incus) behalten ihren ContainerLauncher – der ist schon abgeschottet.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from hydrahive.tools._launcher import Launcher, get_launcher

logger = logging.getLogger(__name__)

SANDBOX_TYPES = frozenset({"project", "specialist"})


def enabled() -> bool:
    return os.environ.get("HH_AGENT_SANDBOX", "").strip().lower() in {"1", "on", "true", "yes"}


def _agent_type(agent_id: str) -> str | None:
    from hydrahive.tools._shell_guard import agent_type
    return agent_type(agent_id)


def wants_sandbox(ctx) -> bool:
    if not enabled():
        return False
    kind = _agent_type(ctx.agent_id)
    return kind is None or kind in SANDBOX_TYPES


def _linked_read_only(ctx, project: dict | None) -> list[Path]:
    """Verknüpfte Projekte, die dieser Lauf lesen darf (gleiche Regel wie projects/_linked.effective)."""
    if not project or not project.get("linked_projects"):
        return []
    try:
        from hydrahive.agents import config as agent_config
        from hydrahive.projects._linked import effective
        from hydrahive.projects._paths import workspace_path
        agent = agent_config.get(ctx.agent_id)
        return [workspace_path(pid) for pid in effective(agent, ctx.project_id, ctx.user_id)]
    except Exception:  # noqa: BLE001 – im Zweifel nichts zusätzlich einblenden
        logger.warning("Sandbox: verknüpfte Projekte nicht lesbar – blende keine ein", exc_info=True)
        return []


def host_launcher(ctx, project: dict | None) -> Launcher:
    if not wants_sandbox(ctx):
        return get_launcher()
    from hydrahive.tools._launcher_sandbox import SandboxLauncher
    return SandboxLauncher(Path(ctx.workspace), read_only=_linked_read_only(ctx, project))
