"""web_browser: Fehlermeldungen sichtbar machen, url + eigenes `page` (02.10.2026).

Befund (Task e98a9263): 29 Fehlschläge seit 01.09., alle nur „dev-browser exit 1“.
- 19× url-Parameter + eigenes `const page = …` im Skript → das Werkzeug stellte
  selbst `const page` voran → Doppel-Deklaration → Syntaxfehler.
- Der echte Grund (Zertifikat, Timeout, Skriptfehler) stand in stderr, landete
  aber nur in ToolResult.metadata — der Agent sah ihn nie.

Die Tests ersetzen dev-browser durch einen Fake (kein Chromium nötig) und
prüfen, welches Skript ankommt und welche Meldung der Agent bekommt.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from hydrahive.tools import web_browser as wb
from hydrahive.tools.base import ToolContext


def _ctx() -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=Path("/tmp"))


@pytest.fixture
def fake(monkeypatch, tmp_path):
    """dev-browser-Ersatz: merkt sich das Skript, liefert vorgegebene Antwort."""
    state = {"script": None, "result": (0, "ok\n", "")}

    async def run(script, env, timeout):
        state["script"] = script
        return state["result"]

    monkeypatch.setattr(wb, "_run_dev_browser", run)
    monkeypatch.setattr(wb.shutil, "which", lambda name: "/usr/bin/dev-browser")
    monkeypatch.setattr(wb.os.path, "expanduser", lambda p: str(tmp_path / "home"))
    return state


def _call(args):
    return asyncio.run(wb._execute(args, _ctx()))


# --- url + eigenes page ------------------------------------------------------

def test_url_preamble_and_own_const_page_do_not_collide(fake):
    """Der häufigste Fehler: url + Skript, das selbst `const page` schreibt."""
    _call({"url": "https://example.com", "script": 'const page = await browser.getPage("main");\nconsole.log(1);'})

    script = fake["script"]
    pre, user = script.split("// --- Skript des Agenten ---", 1)
    assert "const page" not in pre                      # Vorspann darf page nicht const binden
    assert "let page = await browser.getPage(" in pre
    assert "goto(\"https://example.com\"" in pre
    # Agenten-Skript steckt in einem eigenen Block → eigene Deklaration erlaubt.
    assert user.lstrip().startswith("try {\n{")
    assert 'const page = await browser.getPage("main");' in user


def test_url_preamble_page_is_usable_without_own_getpage(fake):
    _call({"url": "https://example.com", "script": "console.log(await page.title());"})

    pre, user = fake["script"].split("// --- Skript des Agenten ---", 1)
    assert "let page" in pre and "await page.title()" in user


def test_url_is_json_quoted_not_python_repr(fake):
    """repr() erzeugt bei Anführungszeichen in der URL ungültiges JS."""
    _call({"url": "https://example.com/?q=it's \"x\"", "script": "console.log(1);"})

    pre = fake["script"].split("// --- Skript des Agenten ---", 1)[0]
    assert 'goto("https://example.com/?q=it\'s \\"x\\""' in pre


def test_script_without_url_is_wrapped_but_unchanged(fake):
    _call({"script": "console.log(42);"})

    assert "console.log(42);" in fake["script"]
    assert "browser.getPage" not in fake["script"].split("// --- Skript des Agenten ---", 1)[0]


# --- Fehlermeldung an den Agenten -------------------------------------------

def test_runtime_error_reason_reaches_the_agent(fake):
    fake["result"] = (1, "", "SKRIPTFEHLER: net::ERR_CERT_AUTHORITY_INVALID at https://192.168.178.217/\nCall log:\n"
                             "\x1b[2m  - navigating to \"https://192.168.178.217/\"\x1b[22m\n")
    res = _call({"script": "console.log(1);"})

    assert res.success is False
    assert "ERR_CERT_AUTHORITY_INVALID" in res.error
    assert "\x1b[" not in res.error                       # Farbcodes entfernt
    assert "selbst ausgestellt" in res.error              # verständlicher Hinweis


def test_colour_codes_removed_from_untagged_errors(fake):
    """Fehler ohne Kennung (z. B. Daemon-Probleme) gehen roh durch — ohne Farbcodes."""
    fake["result"] = (1, "", "\x1b[2mdaemon kaputt\x1b[22m\n")
    res = _call({"script": "console.log(1);"})

    assert "daemon kaputt" in res.error
    assert "\x1b[" not in res.error


def test_syntax_error_gets_a_readable_hint_with_agent_line(fake):
    """Syntaxfehler: dev-browser liefert nur „at user-script.js:N:M“.

    Gemessen am 02.10. mit echtem dev-browser: Syntaxfehler in Agenten-Zeile 3
    ohne url → user-script.js:19 (dev-browser 13 Zeilen + Hülle 3 Zeilen).
    """
    fake["result"] = (1, "", "    at user-script.js:19:11\n\n")
    res = _call({"script": "console.log(1);\nconsole.log(2);\nconst x = ;"})

    assert res.success is False
    assert "Syntaxfehler im Skript (Zeile 3)" in res.error


def test_line_number_accounts_for_url_preamble(fake):
    """Mit url 2 Zeilen mehr Vorspann: Agenten-Zeile 3 → user-script.js:21."""
    fake["result"] = (1, "", "    at user-script.js:21:11\n\n")
    res = _call({"url": "https://example.com", "script": "a;\nb;\nconst x = ;"})

    assert "(Zeile 3)" in res.error


def test_reference_error_hint_for_missing_getpage(fake):
    fake["result"] = (1, "", "SKRIPTFEHLER: ReferenceError: 'page' is not defined\n    at <anonymous> (user-script.js:15:7)\n")
    res = _call({"script": "await page.reload();"})

    assert "'page' is not defined" in res.error
    assert "browser.getPage" in res.error


def test_partial_output_before_the_error_is_kept(fake):
    fake["result"] = (1, "Titel: Beispiel\n", "SKRIPTFEHLER: Timeout 2000ms exceeded.\n")
    res = _call({"script": "console.log(1);"})

    assert "Timeout 2000ms exceeded" in res.error
    assert "Titel: Beispiel" in res.error


def test_error_text_is_capped(fake):
    fake["result"] = (1, "x" * 50_000, "SKRIPTFEHLER: " + "y" * 50_000)
    res = _call({"script": "console.log(1);"})

    assert len(res.error) < 6_000


def test_success_path_unchanged(fake):
    fake["result"] = (0, "TITEL: Example Domain\n", "")
    res = _call({"url": "https://example.com", "script": "console.log(1);"})

    assert res.success is True
    assert res.output == "TITEL: Example Domain\n"


# --- Installer (installer/modules/87-mcp-servers.sh) -------------------------
# Auf hydratest (02.10.) ausgeführt: meldete „Chromium installiert“, installiert
# war nichts. `dev-browser install --yes` → „unexpected argument '--yes'“,
# Fehler per 2>/dev/null || true verschluckt; außerdem lief es als root.

MCP = Path(__file__).resolve().parents[2] / "installer" / "modules" / "87-mcp-servers.sh"


def _code(path: Path) -> str:
    """Skript ohne Kommentarzeilen — Kommentare erklären den alten Fehler."""
    return "\n".join(line for line in path.read_text().splitlines() if not line.lstrip().startswith("#"))


def test_installer_calls_dev_browser_install_without_unknown_flag():
    text = _code(MCP)

    assert "dev-browser install --yes" not in text
    assert 'sudo -u "$HH_USER" env HOME="$DEV_BROWSER_HOME" dev-browser install' in text


def test_installer_checks_the_real_runtime_files_and_does_not_hide_errors():
    text = _code(MCP)
    block = text.split("dev-browser installieren", 1)[1].split('log "MCP-Server:', 1)[0]

    # Bedingung prüft beides, was der Daemon braucht (Laufzeit UND Chromium) —
    # auf hydratest fehlte die Laufzeit, Chromium-Ordner allein hätte nichts gesagt.
    cond = next(line for line in block.splitlines() if line.lstrip().startswith("if [ ! -d"))
    assert '.dev-browser/node_modules" ]' in cond and '.cache/ms-playwright" ]' in cond
    assert "2>/dev/null || true" not in block
    assert "WARNUNG" in block                     # Fehlschlag wird sichtbar gemeldet
