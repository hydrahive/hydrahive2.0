"""Ghostflix-Scraper — Login + episodes_data parsen."""
from __future__ import annotations

import json
import logging
import re

import httpx

logger = logging.getLogger(__name__)

_LOGIN_URL = "https://ghostflix.tv/wp-login.php"
_EPISODES_RE = re.compile(r'var\s+episodes_data\s*=\s*(\{.*?\});', re.DOTALL)
# Fallback: window object assignment pattern
_ASSIGN_RE = re.compile(
    r'episodes_data\["([^"]+)"\]\["bunny_video_id"\]\s*=\s*"([^"]+)"'
)
_LIBRARY_RE = re.compile(
    r'episodes_data\["([^"]+)"\]\["bunny_library_id"\]\s*=\s*"([^"]+)"'
)
_TITLE_RE = re.compile(r'<h1[^>]*class="[^"]*entry-title[^"]*"[^>]*>([^<]+)<')
_SEASON_RE = re.compile(r'[Ss]taffel\s*(\d+)|[Ss]eason\s*(\d+)', re.IGNORECASE)


async def scrape_series(url: str, username: str, password: str) -> dict:
    """
    Meldet sich bei Ghostflix an und gibt die Episodenliste zurück.

    Returns:
        {
          "title": str,
          "season": int,
          "episodes": [{"key": str, "episode": int, "bunny_video_id": str,
                        "bunny_library_id": str, "bunny_video_type": str}]
        }
    """
    async with httpx.AsyncClient(
        follow_redirects=True, timeout=20.0
    ) as client:
        await _login(client, username, password)
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    title = _parse_title(html, url)
    season = _parse_season(title, url)
    episodes = _parse_episodes(html)

    if not episodes:
        raise ValueError(
            "Keine Episoden gefunden — Token korrekt? Ghostflix-Login prüfen."
        )

    return {"title": title, "season": season, "episodes": episodes}


async def _login(client: httpx.AsyncClient, username: str, password: str) -> None:
    resp = await client.post(
        _LOGIN_URL,
        data={
            "log": username,
            "pwd": password,
            "wp-submit": "Log In",
            "redirect_to": "/",
            "rememberme": "forever",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    # WordPress redirects to / on success; check for login page in response
    if "wp-login.php" in str(resp.url) and "incorrect" in resp.text.lower():
        raise ValueError("Ghostflix-Login fehlgeschlagen — Benutzername oder Passwort falsch")


def _parse_title(html: str, url: str) -> str:
    m = _TITLE_RE.search(html)
    if m:
        return m.group(1).strip()
    # Fallback: last segment of URL
    segment = url.rstrip("/").rsplit("/", 1)[-1]
    return segment.replace("-", " ").title()


def _parse_season(title: str, url: str) -> int:
    for text in (title, url):
        m = _SEASON_RE.search(text)
        if m:
            return int(m.group(1) or m.group(2))
    return 1


def _parse_episodes(html: str) -> list[dict]:
    # Try window.episodes_data JSON first
    m = _EPISODES_RE.search(html)
    if m:
        try:
            data = json.loads(m.group(1))
            return _episodes_from_dict(data)
        except json.JSONDecodeError:
            pass

    # Fallback: key=value assignment pattern
    video_ids: dict[str, str] = {}
    library_ids: dict[str, str] = {}
    for key, vid in _ASSIGN_RE.findall(html):
        video_ids[key] = vid
    for key, lid in _LIBRARY_RE.findall(html):
        library_ids[key] = lid

    if not video_ids:
        return []

    return _episodes_from_dict({
        key: {
            "bunny_video_id": vid,
            "bunny_library_id": library_ids.get(key, ""),
            "episode_video_display": "bunny",
            "bunny_video_type": "mp4",
        }
        for key, vid in video_ids.items()
    })


def _episodes_from_dict(data: dict) -> list[dict]:
    episodes = []
    for key, meta in data.items():
        if meta.get("episode_video_display") != "bunny":
            continue
        ep_num = _extract_ep_number(key)
        episodes.append({
            "key": key,
            "episode": ep_num,
            "bunny_video_id": meta.get("bunny_video_id", ""),
            "bunny_library_id": meta.get("bunny_library_id", ""),
            "bunny_video_type": meta.get("bunny_video_type", "mp4"),
        })
    episodes.sort(key=lambda e: e["episode"])
    return episodes


def _extract_ep_number(key: str) -> int:
    # "Video-Season-1-Ep-3" → 3
    m = re.search(r'[Ee]p[-_]?(\d+)$', key)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)$', key)
    return int(m.group(1)) if m else 0
