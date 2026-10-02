"""Health-Check der Websuche (SearXNG).

Hintergrund: SearXNG war vom 29.08. bis 26.09.2026 ausgefallen — der Dienst
stürzte 364.199 Mal ab (systemd startete ihn jedes Mal neu), das
web_search-Tool meldete nur pro Aufruf "Request fehlgeschlagen", und niemand
bemerkte es vier Wochen lang. Agents arbeiteten in der Zeit ohne Websuche.

Der Check prüft nicht nur, ob der Port offen ist, sondern schickt eine echte
Suchanfrage mit format=json — genau wie das Tool. Ein laufender Prozess, der
keine Ergebnisse liefert (z.B. alle Engines gesperrt), gilt ebenfalls als
Ausfall.
"""
from __future__ import annotations

import logging

import httpx

from hydrahive.settings.overrides import resolve as resolve_setting
from hydrahive.tools._searx_outage import describe, unavailable_engines

logger = logging.getLogger(__name__)

_TIMEOUT_S = 6.0
_PROBE_QUERY = "wikipedia"


def websearch_health() -> dict:
    """Status der Websuche fürs Dashboard.

    configured=False  → keine URL hinterlegt, Anzeige "aus"
    ok=False          → konfiguriert, aber keine verwertbaren Ergebnisse
    unavailable       → gesperrte Suchanbieter ({engine, reason}), auch bei ok=True
    """
    base = (resolve_setting("searxng_url") or "").rstrip("/")
    if not base:
        return {"ok": False, "configured": False, "detail": "nicht konfiguriert"}

    try:
        r = httpx.get(
            f"{base}/search",
            params={"q": _PROBE_QUERY, "format": "json"},
            timeout=_TIMEOUT_S,
        )
        r.raise_for_status()
        data = r.json() or {}
        results = data.get("results") or []
    except httpx.HTTPError as e:
        logger.warning("Websuche nicht erreichbar: %s", e)
        return {"ok": False, "configured": True, "detail": f"nicht erreichbar: {type(e).__name__}"}
    except ValueError:
        return {"ok": False, "configured": True, "detail": "Antwort ist kein JSON"}

    # Gesperrte Anbieter (CAPTCHA, zu viele Anfragen …) mitmelden — am 02.10.2026
    # waren alle gesperrt und die Websuche lieferte unbemerkt 0 Treffer.
    unavailable = unavailable_engines(data)
    if not results:
        detail = f"keine Ergebnisse — gesperrt: {describe(unavailable)}" if unavailable else "keine Ergebnisse"
        return {"ok": False, "configured": True, "detail": detail, "unavailable": unavailable}
    detail = f"{len(results)} Ergebnisse"
    if unavailable:
        detail += " · ausgefallen: " + ", ".join(u["engine"] for u in unavailable)
    return {"ok": True, "configured": True, "detail": detail, "unavailable": unavailable}
