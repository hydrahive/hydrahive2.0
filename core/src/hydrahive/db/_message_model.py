from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    id: str
    session_id: str
    role: str
    content: Any
    created_at: str = ""
    token_count: int | None = None
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Message":
        raw = row["content"]
        try:
            content = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            content = raw
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=content,
            created_at=row["created_at"],
            token_count=row["token_count"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )
