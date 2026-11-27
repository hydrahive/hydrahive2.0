"""Agent löschen – direkt, ohne Archiv (internes Aufräumen, z. B. Storyteller).

Nimmt den eigenen Arbeitsordner mit, sonst entstehen Waisen (Spec archiv-system.md,
Etappe 2). Der Projekt-Agent teilt sich den Ordner mit dem Projekt – der bleibt.
Ins Archiv packt vorher archive/deletion.py.

Diese Funktion ist der eine Ort, an dem der Agentenordner wirklich verschwindet – jeder
Lösch-Weg (Archiv über archive/_remove.py:agent(), externe Instanzen, interne Aufräumer)
läuft am Ende hier durch. Deshalb räumt sie hier auch die Freigabe in allowed_specialists
auf (Review PR #722, Fund 15.11.2026): sonst bleibt die ID als tote Freigabe in jedem
Projekt stehen, das den Agenten einmal freigegeben hatte.
"""
from __future__ import annotations

import logging
import shutil

from hydrahive.agents._config_utils import get
from hydrahive.agents._paths import agent_dir, workspace_for

logger = logging.getLogger(__name__)


def delete(agent_id: str) -> bool:
    d = agent_dir(agent_id)
    if not d.exists():
        return False
    cfg = get(agent_id)
    if cfg and cfg.get("type") != "project":
        from hydrahive.archive.safe_rm import remove_tree
        remove_tree(workspace_for(cfg))
    shutil.rmtree(d)
    _revoke_allowance(agent_id)
    from hydrahive.agents import _tool_pool_cleanup
    _tool_pool_cleanup.remove_agent(agent_id)
    logger.info("Agent gelöscht: %s", agent_id)
    return True


def _revoke_allowance(agent_id: str) -> None:
    """Tote Freigabe entfernen: die ID aus allowed_specialists jedes Projekts, das sie führt.
    Lazy-Import gegen den Zyklus agents.config <-> projects.config."""
    from hydrahive.projects import config as project_config
    for p in project_config.list_all():
        allowed = p.get("allowed_specialists") or []
        if agent_id in allowed:
            project_config.update(p["id"], allowed_specialists=[s for s in allowed if s != agent_id])
