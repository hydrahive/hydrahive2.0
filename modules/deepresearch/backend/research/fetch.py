"""Seite holen + zu Text reduzieren + OG-Image ziehen.

Nutzt die SSRF-sichere safe_async_client aus dem Core (DNS-Pinning gegen Rebinding).
HTML→Text ist bewusst grob (Regex) — der Extraktions-LLM liest den Text, perfekte
Extraktion ist nicht nötig.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from hydrahive.net.ssrf import SsrfBlocked, safe_async_client

logger = logging.getLogger(__name__)

_MAX_CHARS = 15_000
_OG = re.compile(
    r'<meta[^>]+(?:property|name)\s*=\s*["\'](?:og:image|twitter:image)["\'][^>]*'
    r'content\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_OG_REV = re.compile(
    r'<meta[^>]+content\s*=\s*["\']([^"\']+)["\'][^>]*'
    r'(?:property|name)\s*=\s*["\'](?:og:image|twitter:image)["\']',
    re.IGNORECASE,
)
_DROP = re.compile(r"<(script|style|noscript|template)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\n\s*\n\s*\n+")
_BAD_IMG = (".svg", ".ico", ".gif")


def _og_image(html: str, base_url: str) -> str:
    m = _OG.search(html) or _OG_REV.search(html)
    if not m:
        return ""
    url = m.group(1).strip()
    if not url or url.lower().endswith(_BAD_IMG):
        return ""
    return urljoin(base_url, url)


def _to_text(html: str) -> str:
    html = _DROP.sub(" ", html)
    text = _TAG.sub(" ", html)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    text = "\n".join(line.strip() for line in text.splitlines())
    text = _WS.sub("\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    return text[:_MAX_CHARS]


async def fetch_page(url: str) -> tuple[str, str]:
    """(text, og_image). Bei Fehler: ("", "")."""
    try:
        async with safe_async_client(url, timeout=20) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (HydraHive DeepResearch)"})
    except SsrfBlocked as e:
        logger.info("deepresearch: fetch SSRF-geblockt %s: %s", url, e)
        return "", ""
    except Exception as e:  # noqa: BLE001 - Web-Fetch ist beste-Effort; toter Link darf den Lauf nicht killen
        logger.info("deepresearch: fetch fehlgeschlagen %s: %s", url, e)
        return "", ""
    ctype = r.headers.get("content-type", "")
    if "html" not in ctype and "text" not in ctype:
        return "", ""
    html = r.text
    return _to_text(html), _og_image(html, url)
