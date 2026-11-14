"""Streaming-Versuche auf EINEM Modell – Baustein der Modellkette in `_call.py`.

Wiederholregeln je Modell (unverändert seit der Messung hydratest 5.11.2026):
- Verbindungsaussetzer (`_CONNECTION_ERRORS`, z. B. stehender Codex-Stream): bis zu STALL_ATTEMPTS Versuche.
- Sonstige Fehler: genau eine Wiederholung, und nur als erster Fehler.
- Nach gesendetem Text keine Wiederholung (sonst doppelter Text).
Neu (Spec agent-templates.md Kap. 8): Anbieterfehler (Limit, Quota, Überlast, Login) brechen sofort ab, wenn
ein weiteres Modell in der Kette wartet – eine Wiederholung beim selben Anbieter hilft dort nicht.

Die Stream-Funktion wird übergeben (nicht importiert), damit Tests sie an `_call` austauschen können.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable

import httpx

from hydrahive.runner._codex_provider import CodexModelNotAllowed, CodexStreamStall
from hydrahive.runner._failover import PROVIDER_CATEGORIES, classify
from hydrahive.runner.events import Event, MessageStart, TextDelta
from hydrahive.runner.llm_bridge_stream import StreamingNotSupported

# Logger + sleep über `_call` (bestehende Tests patchen `_call.asyncio.sleep` und lesen den Logger von `_call`).
logger = logging.getLogger("hydrahive.runner._call")

# Eine stehende Codex-Verbindung (CodexStreamStall) betrifft die Verbindung, nicht die Anfrage: Der sofortige neue
# Versuch war in der Messung (hydratest 5.11.2026, 60 Läufe) fast immer erfolgreich. Darum bis zu 5 Stream-Versuche,
# jeweils neue Verbindung. Andere Fehler behalten ihre bisherige Regel (1 Wiederholung, dann Fallback).
STALL_ATTEMPTS = 5
# Verbindungsfehler von httpx (Messung: 2 von 60 echten Anfragen, mit LEERER Meldung) sind dieselbe Sorte Aussetzer
# wie ein Stall: die Verbindung, nicht die Anfrage. Bewusst NICHT: HTTPStatusError (eine Antwort),
# UnsupportedProtocol/ProxyError/LocalProtocolError (dauerhaft), PoolTimeout (Überlast).
_CONNECTION_ERRORS = (
    CodexStreamStall, httpx.ReadError, httpx.ConnectError, httpx.WriteError, httpx.RemoteProtocolError,
    httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout,
)
_STALL_PAUSE = 0.5
_USAGE_KEYS = ("input_tokens", "output_tokens", "cache_creation_tokens", "cache_read_tokens")


@dataclass
class StreamOutcome:
    ok: bool = False
    not_supported: bool = False
    text_sent: bool = False
    reason: str | None = None
    blocks: list[dict] = field(default_factory=list)
    stop_reason: str = ""
    usage: dict[str, int] = field(default_factory=dict)


async def stream_attempts(
    stream_fn: Callable[..., AsyncIterator[dict[str, Any]]],
    kwargs: dict[str, Any],
    out: StreamOutcome,
    *,
    has_next: bool,
) -> AsyncIterator[Event]:
    """Streamt ein Modell mit den Wiederholregeln. Ergebnis steht danach in `out`."""
    other_retried = False
    for attempt in range(STALL_ATTEMPTS):
        out.text_sent = False
        out.reason = None
        try:
            async for raw_ev in stream_fn(**kwargs):
                t = raw_ev.get("type")
                if t == "message_start":
                    yield MessageStart()
                elif t == "text_delta":
                    yield TextDelta(text=raw_ev.get("text", ""))
                    out.text_sent = True
                elif t == "message_stop":
                    out.blocks = raw_ev.get("blocks", [])
                    out.stop_reason = raw_ev.get("stop_reason", "")
                    out.usage = {k: int(raw_ev.get(k, 0) or 0) for k in _USAGE_KEYS}
                    out.ok = True
                    break
            return
        except StreamingNotSupported as e:
            logger.info("Streaming nicht unterstützt: %s — Fallback", e)
            out.not_supported = True
            return
        except CodexModelNotAllowed:
            raise
        except Exception as e:
            out.reason = classify(e)
            if out.text_sent:
                logger.warning("Stream-Fehler nach Text — Fallback auf non-streaming: %s: %s", type(e).__name__, e)
                return
            if has_next and out.reason in PROVIDER_CATEGORIES:
                logger.warning("Stream-Fehler (%s) — nächstes Modell: %s: %s", out.reason, type(e).__name__, e)
                return
            is_stall = isinstance(e, _CONNECTION_ERRORS)
            can_retry = (is_stall and attempt < STALL_ATTEMPTS - 1) or (
                not is_stall and not other_retried and attempt == 0)
            if not can_retry:
                logger.warning("Stream-Fehler — kein weiterer Versuch auf diesem Modell: %s: %s", type(e).__name__, e)
                return
            wait = _STALL_PAUSE if is_stall else 1.5
            logger.warning("Stream-Fehler (Versuch %d) — retry in %gs: %s: %s", attempt + 1, wait, type(e).__name__, e)
            other_retried = other_retried or not is_stall
            from hydrahive.runner import _call
            await _call.asyncio.sleep(wait)
