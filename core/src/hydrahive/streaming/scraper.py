"""Ghostflix-Scraper — Playwright-basierter Login + episodes_data parsen."""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_EPISODES_RE = re.compile(r'var\s+episodes_data\s*=\s*(\{.*?\});', re.DOTALL)
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
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright nicht installiert. Auf dem Server ausführen: "
            "pip install playwright && playwright install chromium"
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            await _login(page, username, password)

            # "load" wartet bis alle Scripte ausgeführt sind (nicht nur DOM ready)
            await page.goto(url, wait_until="load", timeout=30_000)

            current_url = page.url
            if "kein-zugriff" in current_url or "restricted" in current_url:
                raise ValueError(
                    "Kein Zugriff auf diese Serie — Abo prüfen oder andere URL verwenden."
                )

            # Direkter Zugriff auf window.episodes_data aus dem JS-Kontext —
            # zuverlässiger als Regex auf HTML wenn die Daten per Script gesetzt werden.
            js_data = await page.evaluate(
                "() => (typeof window.episodes_data !== 'undefined') "
                "? window.episodes_data : null"
            )
            html = await page.content()
        finally:
            await browser.close()

    title = _parse_title(html, url)
    season = _parse_season(title, url)

    if js_data:
        episodes = _episodes_from_dict(js_data)
    else:
        episodes = _parse_episodes(html)

    logger.debug(
        "Scrape %s: title=%r season=%d js_data=%s html_len=%d episodes=%d",
        url, title, season, bool(js_data), len(html), len(episodes),
    )

    if not episodes:
        logger.warning(
            "Keine Episoden gefunden. URL: %s. js_data=%s. HTML-Snippet: %s",
            current_url, js_data, html[:500],
        )
        raise ValueError(
            "Keine Episoden gefunden — Serie hat keine Bunny-Videos oder Struktur unbekannt."
        )

    return {"title": title, "season": season, "episodes": episodes}


async def _login(page, username: str, password: str) -> None:
    await page.goto(
        "https://ghostflix.tv/wp-login.php",
        wait_until="domcontentloaded",
        timeout=20_000,
    )
    await page.fill("#user_login", username)
    await page.fill("#user_pass", password)
    await page.click("#wp-submit")

    # Warten bis Redirect nach Login abgeschlossen
    try:
        await page.wait_for_url(
            lambda u: "wp-login.php" not in u,
            timeout=10_000,
        )
    except Exception:
        pass  # Timeout ist OK — manchmal bleibt WP kurz auf login.php

    if "wp-login.php" in page.url:
        html = await page.content()
        if any(w in html.lower() for w in ("incorrect", "error", "falsch", "ungültig")):
            raise ValueError(
                "Ghostflix-Login fehlgeschlagen — Benutzername oder Passwort falsch."
            )
    logger.debug("Login erfolgreich, aktuelle URL: %s", page.url)


def _parse_title(html: str, url: str) -> str:
    m = _TITLE_RE.search(html)
    if m:
        return m.group(1).strip()
    segment = url.rstrip("/").rsplit("/", 1)[-1]
    return segment.replace("-", " ").title()


def _parse_season(title: str, url: str) -> int:
    for text in (title, url):
        m = _SEASON_RE.search(text)
        if m:
            return int(m.group(1) or m.group(2))
    return 1


def _parse_episodes(html: str) -> list[dict]:
    m = _EPISODES_RE.search(html)
    if m:
        try:
            data = json.loads(m.group(1))
            return _episodes_from_dict(data)
        except json.JSONDecodeError as e:
            logger.debug("Scraper: JSON-Parse fehlgeschlagen, versuche Regex-Fallback: %s", e)

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
    m = re.search(r'[Ee]p[-_]?(\d+)$', key)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)$', key)
    return int(m.group(1)) if m else 0
