"""Agent löschen – direkt, ohne Archiv (internes Aufräumen, z. B. Storyteller).

Nimmt den eigenen Arbeitsordner mit, sonst entstehen Waisen (Spec archiv-system.md,
Etappe 2). Der Projekt-Agent teilt sich den Ordner mit dem Projekt – der bleibt.
Ins Archiv packt vorher archive/deletion.py.
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
    logger.info("Agent gelöscht: %s", agent_id)
    return True
