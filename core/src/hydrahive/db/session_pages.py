"""Paginierte, benutzergebundene Sessionliste für die Chatoberfläche."""
from __future__ import annotations

from hydrahive.db.connection import db
from hydrahive.db.sessions import Session

MAX_SESSION_PAGE_OFFSET = 10_000

_COUNT_SQL = """
    SELECT COUNT(*)
    FROM sessions AS s
    WHERE s.user_id = ?
      AND (? IS NULL OR s.project_id = ?)
      AND (? = 0 OR s.project_id IS NULL)
      AND (
          ? = 1
          OR NOT EXISTS (
              SELECT 1 FROM agent_handoffs AS ah WHERE ah.session_id = s.id
          )
          OR CASE
              WHEN json_valid(s.metadata)
              THEN json_type(s.metadata, '$.user_visible') = 'true'
              ELSE 0
          END
      )
"""

_ITEMS_SQL = """
    SELECT s.*
    FROM sessions AS s
    WHERE s.user_id = ?
      AND (? IS NULL OR s.project_id = ?)
      AND (? = 0 OR s.project_id IS NULL)
      AND (
          ? = 1
          OR NOT EXISTS (
              SELECT 1 FROM agent_handoffs AS ah WHERE ah.session_id = s.id
          )
          OR CASE
              WHEN json_valid(s.metadata)
              THEN json_type(s.metadata, '$.user_visible') = 'true'
              ELSE 0
          END
      )
    ORDER BY s.updated_at DESC, s.id DESC
    LIMIT ? OFFSET ?
"""


def list_page_for_user(
    user_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    project_id: str | None = None,
    unassigned: bool = False,
    include_internal: bool = False,
) -> tuple[list[Session], int]:
    if not 1 <= limit <= 200 or not 0 <= offset <= MAX_SESSION_PAGE_OFFSET:
        raise ValueError("invalid session page bounds")
    if project_id is not None and unassigned:
        raise ValueError("conflicting session scope")
    params = (
        user_id,
        project_id,
        project_id,
        int(unassigned),
        int(include_internal),
    )
    with db() as conn:
        total = conn.execute(_COUNT_SQL, params).fetchone()[0]
        rows = conn.execute(_ITEMS_SQL, (*params, limit, offset)).fetchall()
    return [Session.from_row(row) for row in rows], total
