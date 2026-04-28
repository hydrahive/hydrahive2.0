"""Persistence + history-resolution helpers for compaction."""
from __future__ import annotations

import logging
import re

from hydrahive.compaction.hooks import CompactionContext
from hydrahive.db import messages as messages_db

logger = logging.getLogger(__name__)


def resolve_through_compaction(messages: list) -> list:
    """Return the latest "visible" view: virtual summary placeholder + kept tail.

    Used during compaction to know what's currently visible BEFORE the new
    compaction is appended. When a previous compaction exists, we work on
    the kept-portion only — never re-summarize already-summarized text.
    """
    latest_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].role == "compaction":
            latest_idx = i
            break
    if latest_idx is None:
        return messages
    cmp_msg = messages[latest_idx]
    first_kept = (cmp_msg.metadata or {}).get("firstKeptEntryId")
    if not first_kept:
        return messages
    kept_from = next((i for i, m in enumerate(messages) if m.id == first_kept), None)
    if kept_from is None or kept_from <= latest_idx:
        return messages
    return [cmp_msg] + messages[kept_from:]


def previous_summary_text(visible: list) -> str | None:
    if visible and visible[0].role == "compaction":
        return visible[0].content if isinstance(visible[0].content, str) else None
    return None


def persist_compaction(
    session_id: str,
    kept: list,
    summary: str,
    ctx: CompactionContext,
    details: dict,
    *,
    source: str,
) -> dict:
    first_kept_id = kept[0].id if kept else ""
    metadata = {
        "firstKeptEntryId": first_kept_id,
        "tokensBefore": ctx.tokens_before,
        "isSplitTurn": ctx.is_split_turn,
        "source": source,
        **details,
    }
    rec = messages_db.append(session_id, "compaction", summary, metadata=metadata)
    logger.info(
        "Session %s kompaktiert (source=%s): %d → %d Messages, summary %d Zeichen",
        session_id, source, len(ctx.messages_before_cut), len(kept), len(summary),
    )
    return {
        "id": rec.id,
        "first_kept": first_kept_id,
        "tokens_before": ctx.tokens_before,
        "summarized_count": len(ctx.messages_before_cut),
        "kept_count": len(kept),
    }


_FILE_PATH_RE = re.compile(r"['\"]([./~][\w\-./]*\.[\w]{1,8})['\"]")


def extract_files(messages: list) -> dict:
    """Cumulative file tracking — extract paths from tool_use blocks."""
    read_files: set[str] = set()
    modified_files: set[str] = set()
    for m in messages:
        if m.role != "assistant" or not isinstance(m.content, list):
            continue
        for block in m.content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            tool = block.get("name", "")
            args = block.get("input") or {}
            path = args.get("path")
            if not path:
                continue
            if tool == "file_read":
                read_files.add(path)
            elif tool in {"file_write", "file_patch"}:
                modified_files.add(path)
    return {"readFiles": sorted(read_files), "modifiedFiles": sorted(modified_files)}
