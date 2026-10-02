"""Skript-Hülle und Fehlertexte für das web_browser-Werkzeug.

Befund 02.10.2026 (Task e98a9263, 29 Fehlschläge seit 01.09.):
- Mit ``url`` stellte das Werkzeug ``const page = …`` voran. Schrieb das Skript
  selbst ``const page = …`` (wie die Werkzeugbeschreibung es zeigt), war ``page``
  doppelt deklariert → Syntaxfehler → „dev-browser exit 1“.
- Der eigentliche Grund stand in stderr, der Agent sah nur „exit 1“.

Lösung: Vorspann bindet ``let page`` außen, das Agenten-Skript läuft in einem
eigenen Block (eigene Deklarationen erlaubt) und in try/catch, der die
Fehlermeldung mit Kennung nach stderr schreibt.
"""
from __future__ import annotations

import json
import re

MARKER = "// --- Skript des Agenten ---"
ERR_TAG = "SKRIPTFEHLER: "
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_LINE = re.compile(r"user-script\.js:(\d+):\d+")
_MAX_ERR = 1_500
_MAX_OUT = 2_000

# Hülle um das Agenten-Skript. Der catch-Zweig wirft weiter, damit der
# Exit-Code ≠ 0 bleibt; die Meldung steht vorher mit Kennung in stderr.
_WRAP_OPEN = "try {\n{\n"
_WRAP_CLOSE = (
    "\n}\n} catch (__hhErr) {\n"
    "  const __m = (__hhErr && __hhErr.name && __hhErr.name !== \"Error\" ? __hhErr.name + \": \" : \"\")"
    " + (__hhErr && __hhErr.message ? __hhErr.message : String(__hhErr));\n"
    f"  console.error({json.dumps(ERR_TAG)} + __m);\n"
    "  throw __hhErr;\n"
    "}\n"
)


def build(script: str, url: str) -> tuple[str, int]:
    """Fertiges Skript und Anzahl Zeilen vor dem Agenten-Code (für Zeilenangaben)."""
    pre = ""
    if url:
        pre = (
            "let page = await browser.getPage(\"main\");\n"
            f"await page.goto({json.dumps(url)}, {{waitUntil: \"domcontentloaded\"}});\n"
        )
    head = pre + MARKER + "\n" + _WRAP_OPEN
    return head + script + _WRAP_CLOSE, head.count("\n")


def _agent_line(stderr: str, offset: int) -> int | None:
    """Zeile im Agenten-Skript aus „user-script.js:N“ (dev-browser legt 13 Zeilen davor)."""
    m = _LINE.search(stderr)
    if not m:
        return None
    line = int(m.group(1)) - 13 - offset
    return line if line >= 1 else None


def _hint(reason: str) -> str:
    low = reason.lower()
    if "err_cert" in low:
        return (" — Die Seite hat ein selbst ausgestelltes oder ungültiges Zertifikat "
                "(z. B. Geräte im Heimnetz). Der Browser lehnt solche Seiten ab.")
    if "'page' is not defined" in low:
        return " — Im Skript zuerst `const page = await browser.getPage(\"main\")` holen oder `url` angeben."
    if "not defined" in low and ("require" in low or "process" in low or "fetch" in low):
        return " — Das Skript läuft in QuickJS, nicht Node.js: kein require/process/fetch."
    if "err_name_not_resolved" in low:
        return " — Adresse nicht gefunden (Tippfehler oder Netz)."
    return ""


def error_text(exit_code: int, stdout: str, stderr: str, offset: int) -> str:
    """Verständliche Fehlermeldung für den Agenten."""
    clean = _ANSI.sub("", stderr or "")
    reason = ""
    for line in clean.splitlines():
        if line.startswith(ERR_TAG):
            reason = line[len(ERR_TAG):].strip()
            break
    line_no = _agent_line(clean, offset)
    where = f" (Zeile {line_no})" if line_no else ""
    if reason:
        msg = f"Skriptfehler{where}: {reason[:_MAX_ERR]}{_hint(reason)}"
    elif line_no or "user-script.js" in clean:
        # Kein catch erreicht → Fehler schon beim Einlesen des Skripts.
        msg = (f"Syntaxfehler im Skript{where}. Häufige Ursache: eine Variable doppelt "
               "deklariert oder eine Klammer fehlt.")
    else:
        detail = clean.strip()[:_MAX_ERR]
        msg = f"dev-browser exit {exit_code}" + (f": {detail}" if detail else "")
    out = (stdout or "").strip()
    if out:
        msg += f"\nAusgabe bis zum Fehler:\n{out[:_MAX_OUT]}"
    return msg
