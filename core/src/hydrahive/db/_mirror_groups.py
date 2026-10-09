"""Wissensräume E2a: Gruppen-Wissen und Außenwirkungs-Grenze (docs/specs/knowledge-spaces.md §2.2).

Liefert die Bausteine, die ``_mirror_scope`` in die Sicht eines Agenten einrechnet:
- ``group_usernames``: Mitglieder der freigegebenen Gruppen (ohne den eigenen Nutzer),
- ``master_agent_ids``: Buddys/Master – deren Sitzungen sind persönlich und für Gruppen tabu
  (Entscheidung Till 09.10.: „Familie ohne Buddy“; über den Agent-Typ, weil Buddys auch in Projekten laufen),
- ``has_outward_tools``: Agent kann etwas nach außen tragen → höchstens Stufe ``normal``.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

#: Werkzeuge mit Außenwirkung (Till 09.10.: shell_exec zählt, weil git push/curl möglich).
#: Lesende Discord-Werkzeuge (discord_channels, discord_read) zählen nicht.
OUTWARD_TOOLS: frozenset[str] = frozenset({
    "shell_exec", "web_browser", "fetch_url", "send_mail", "plugin__http-tester__request",
    "discord_post", "discord_reply", "discord_edit", "discord_delete", "discord_message_pin",
    "discord_forum_tags", "discord_thread_manage", "discord_member_manage", "discord_server_manage",
})


def has_outward_tools(tools: list[str] | None) -> bool:
    return any(t in OUTWARD_TOOLS for t in (tools or []))


def group_usernames(group_ids: list[str] | None, *, exclude: str) -> tuple[str, ...]:
    """Nutzernamen aller Mitglieder der Gruppen, sortiert, ohne ``exclude``. Unbekannte Gruppen → nichts."""
    if not group_ids:
        return ()
    from hydrahive.access import store
    from hydrahive.api.middleware.users import get_by_id
    names: set[str] = set()
    for gid in group_ids:
        for uid in store.members_of(str(gid)):
            user = get_by_id(uid)
            if user and user["username"] != exclude:
                names.add(user["username"])
    return tuple(sorted(names))


def master_agent_ids() -> tuple[str, ...]:
    """IDs aller Master-Agenten (Buddys, Assistenten), sortiert."""
    from hydrahive.agents._config_utils import list_all
    return tuple(sorted(a["id"] for a in list_all() if a.get("type") == "master"))
