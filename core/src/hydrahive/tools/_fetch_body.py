"""Ergebnis-Body von fetch_url: roh wie bisher oder als lesbarer Text (Spec websuche-kostenlos §6)."""
from __future__ import annotations

from hydrahive.tools import _html_text

FORMATS = ("raw", "text")
RAW_MAX_BYTES = 200_000          # wie bisher (_MAX_BYTES in fetch_url)
TEXT_MAX_HTML_BYTES = 2_000_000  # HTML wird fast komplett weggeworfen → mehr lesen
TEXT_MAX_CHARS = 50_000
_MIN_TEXT = 200


def body_fields(raw: bytes, content_type: str, fmt: str) -> dict:
    """Felder body/truncated (+ format_applied, title, published, hint) fürs Tool-Ergebnis."""
    if fmt != "text":
        return {"body": raw[:RAW_MAX_BYTES].decode("utf-8", errors="replace"),
                "truncated": len(raw) > RAW_MAX_BYTES}
    if "html" not in (content_type or "").lower():
        return {"body": raw[:RAW_MAX_BYTES].decode("utf-8", errors="replace"),
                "truncated": len(raw) > RAW_MAX_BYTES, "format_applied": "raw"}
    html = raw[:TEXT_MAX_HTML_BYTES].decode("utf-8", errors="replace")
    got = _html_text.extract(html)
    text = got["text"]
    out: dict = {
        "body": text[:TEXT_MAX_CHARS],
        "truncated": len(text) > TEXT_MAX_CHARS or len(raw) > TEXT_MAX_HTML_BYTES,
        "format_applied": "text",
        "title": got["title"],
        "published": got["published"],
    }
    if len(text) < _MIN_TEXT:
        out["hint"] = "Seite braucht vermutlich JavaScript – web_browser nutzen"
    return out
