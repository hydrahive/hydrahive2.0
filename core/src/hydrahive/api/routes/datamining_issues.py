"""Datamining: GitHub + Gitea Issues & PRs importieren."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_admin
from hydrahive.db import mirror

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/datamining/import", tags=["datamining"])

Auth = Annotated[Any, Depends(require_admin)]


# ── Pydantic ──────────────────────────────────────────────────────────────────

class GithubImportRequest(BaseModel):
    owner: str
    repo: str
    token: str = ""


class GiteaImportRequest(BaseModel):
    owner: str
    repo: str
    base_url: str = "http://192.168.3.22:3001"
    token: str = ""


# ── DB-Insert ─────────────────────────────────────────────────────────────────

async def _insert_rows(rows: list[tuple]) -> int:
    if not rows or mirror._pool is None:
        return 0
    async with mirror._pool.acquire() as conn:
        await conn.executemany("""
            INSERT INTO events (id, message_id, session_id, block_index, chunk_index, chunk_total,
                               event_type, created_at, username, agent_name, text,
                               tool_name, tool_use_id, tool_input, tool_output, is_error)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14::jsonb,$15,$16)
            ON CONFLICT (id) DO NOTHING
        """, rows)
    return len(rows)


def _to_row(
    ev_id: str, msg_id: str, session_id: str, block_idx: int,
    ev_type: str, created_at: datetime, username: str | None,
    agent_name: str | None, text: str | None, meta: dict | None,
) -> tuple:
    return (
        ev_id, msg_id, session_id, block_idx, 0, 1,
        ev_type, created_at, username, agent_name, text,
        None, None,
        json.dumps(meta) if meta else None,
        None, False,
    )


def _parse_dt(s: str | None) -> datetime:
    if not s:
        return datetime.now(timezone.utc)
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ── GitHub ────────────────────────────────────────────────────────────────────

async def _fetch_github(owner: str, repo: str, token: str) -> list[tuple]:
    tok = token or os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"

    session_id = f"github-{owner}-{repo}"
    rows: list[tuple] = []
    page = 1

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            r = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                headers=headers,
                params={"state": "all", "per_page": 100, "page": page},
            )
            if r.status_code == 404:
                raise HTTPException(404, f"GitHub repo {owner}/{repo} nicht gefunden")
            if r.status_code == 403:
                raise HTTPException(403, "GitHub: Rate-limit oder Token fehlt")
            r.raise_for_status()
            items = r.json()
            if not items:
                break

            for item in items:
                num = item["number"]
                is_pr = "pull_request" in item
                ev_type = "github_pr" if is_pr else "github_issue"
                msg_id = f"{session_id}-{num}"
                created = _parse_dt(item.get("created_at"))
                text = f"#{num} {item.get('title', '')}\n\n{item.get('body') or ''}"
                meta = {
                    "number": num,
                    "state": item.get("state"),
                    "labels": [lb["name"] for lb in item.get("labels", [])],
                    "url": item.get("html_url"),
                }
                rows.append(_to_row(
                    f"{msg_id}-{ev_type}", msg_id, session_id, 0, ev_type,
                    created, item.get("user", {}).get("login"), f"{owner}/{repo}", text, meta,
                ))

                # Kommentare
                comments_url = item.get("comments_url", "")
                if comments_url and item.get("comments", 0) > 0:
                    cr = await client.get(comments_url, headers=headers)
                    if cr.status_code == 200:
                        for ci, comment in enumerate(cr.json()):
                            cid = comment.get("id", ci)
                            rows.append(_to_row(
                                f"{msg_id}-comment-{cid}", msg_id, session_id, ci + 1,
                                f"{ev_type}_comment", _parse_dt(comment.get("created_at")),
                                comment.get("user", {}).get("login"), f"{owner}/{repo}",
                                comment.get("body"), {"comment_id": cid, "url": comment.get("html_url")},
                            ))

            if len(items) < 100:
                break
            page += 1

    return rows


# ── Gitea ─────────────────────────────────────────────────────────────────────

async def _fetch_gitea(owner: str, repo: str, base_url: str, token: str) -> list[tuple]:
    base = base_url.rstrip("/")
    headers = {"Authorization": f"token {token}"} if token else {}
    session_id = f"gitea-{owner}-{repo}"
    rows: list[tuple] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for issue_type in ("issues", "pulls"):
            ev_base = "gitea_issue" if issue_type == "issues" else "gitea_pr"
            page = 1
            while True:
                r = await client.get(
                    f"{base}/api/v1/repos/{owner}/{repo}/{issue_type}",
                    headers=headers,
                    params={"state": "open", "limit": 50, "page": page},
                )
                if r.status_code == 404:
                    raise HTTPException(404, f"Gitea repo {owner}/{repo} nicht gefunden")
                r.raise_for_status()
                items = r.json()
                if not items:
                    break

                for item in items:
                    num = item["number"]
                    msg_id = f"{session_id}-{num}"
                    created = _parse_dt(item.get("created"))
                    text = f"#{num} {item.get('title', '')}\n\n{item.get('body') or ''}"
                    meta = {
                        "number": num,
                        "state": item.get("state"),
                        "labels": [lb["name"] for lb in item.get("labels", [])],
                        "url": item.get("html_url"),
                    }
                    rows.append(_to_row(
                        f"{msg_id}-{ev_base}", msg_id, session_id, 0, ev_base,
                        created, (item.get("user") or {}).get("login"), f"{owner}/{repo}", text, meta,
                    ))

                    # Kommentare
                    cr = await client.get(
                        f"{base}/api/v1/repos/{owner}/{repo}/issues/{num}/comments",
                        headers=headers,
                    )
                    if cr.status_code == 200:
                        for ci, comment in enumerate(cr.json()):
                            cid = comment.get("id", ci)
                            rows.append(_to_row(
                                f"{msg_id}-comment-{cid}", msg_id, session_id, ci + 1,
                                f"{ev_base}_comment", _parse_dt(comment.get("created")),
                                (comment.get("user") or {}).get("login"), f"{owner}/{repo}",
                                comment.get("body"), {"comment_id": cid},
                            ))

                if len(items) < 50:
                    break
                page += 1

    return rows


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/github", dependencies=[Depends(require_admin)])
async def import_github(body: GithubImportRequest) -> dict:
    if mirror._pool is None:
        raise HTTPException(503, "Mirror nicht aktiv")
    rows = await _fetch_github(body.owner, body.repo, body.token)
    inserted = await _insert_rows(rows)
    logger.info("GitHub %s/%s: %d Events importiert", body.owner, body.repo, inserted)
    return {"ok": True, "inserted": inserted, "source": f"github-{body.owner}-{body.repo}"}


@router.post("/gitea", dependencies=[Depends(require_admin)])
async def import_gitea(body: GiteaImportRequest) -> dict:
    if mirror._pool is None:
        raise HTTPException(503, "Mirror nicht aktiv")
    rows = await _fetch_gitea(body.owner, body.repo, body.base_url, body.token)
    inserted = await _insert_rows(rows)
    logger.info("Gitea %s/%s: %d Events importiert", body.owner, body.repo, inserted)
    return {"ok": True, "inserted": inserted, "source": f"gitea-{body.owner}-{body.repo}"}
