"""Websuche: Health-Check und Schutz gegen Interpreter-Drift.

Hintergrund: SearXNG war vom 29.08. bis 26.09.2026 ausgefallen. Der venv
folgte /usr/bin/python3, das System wechselte auf 3.14, die Pakete lagen
unter lib/python3.12/ — 364.199 Abstürze, vier Wochen ohne Websuche für alle
Agents, und niemand hat es bemerkt, weil nirgends ein Status angezeigt wurde.
"""
from pathlib import Path

import httpx

from hydrahive.api.routes import _websearch_health as wh

INSTALLER = Path(__file__).resolve().parents[2] / "installer"


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)

    def json(self):
        return self._payload


def _url(monkeypatch, value):
    monkeypatch.setattr(wh, "resolve_setting", lambda key: value)


def test_ok_when_search_returns_results(monkeypatch):
    _url(monkeypatch, "http://127.0.0.1:8888")
    monkeypatch.setattr(wh.httpx, "get", lambda *a, **k: _Resp({"results": [{"title": "x"}]}))

    h = wh.websearch_health()

    assert h["ok"] is True
    assert h["configured"] is True


def test_down_when_service_unreachable(monkeypatch):
    """Genau der Fehler vom 29.08.: Prozess crasht, Port antwortet nicht."""
    _url(monkeypatch, "http://127.0.0.1:8888")

    def boom(*a, **k):
        raise httpx.ConnectError("All connection attempts failed")

    monkeypatch.setattr(wh.httpx, "get", boom)

    h = wh.websearch_health()

    assert h["ok"] is False
    assert h["configured"] is True
    assert "nicht erreichbar" in h["detail"]


def test_down_when_running_but_no_results(monkeypatch):
    """Prozess läuft, aber alle Engines gesperrt — für Agents genauso nutzlos."""
    _url(monkeypatch, "http://127.0.0.1:8888")
    monkeypatch.setattr(wh.httpx, "get", lambda *a, **k: _Resp({"results": []}))

    h = wh.websearch_health()

    assert h["ok"] is False
    assert h["detail"] == "keine Ergebnisse"


def test_off_when_not_configured(monkeypatch):
    _url(monkeypatch, "")

    h = wh.websearch_health()

    assert h["configured"] is False


def test_dashboard_health_includes_websearch(monkeypatch):
    """Der Status muss im Dashboard ankommen — sonst bleibt ein Ausfall wieder unsichtbar."""
    from hydrahive.api.routes import _dashboard_helpers as dh

    monkeypatch.setattr(dh, "websearch_health", lambda: {"ok": False, "configured": True, "detail": "x"})

    assert dh.health_check()["websearch"]["ok"] is False


def test_searxng_installer_pins_python312():
    """Neuinstallation darf den venv nicht an das generische python3 binden."""
    text = (INSTALLER / "modules" / "76-searxng.sh").read_text()

    assert 'SEARXNG_PYTHON="/usr/bin/python3.12"' in text
    assert '"$SEARXNG_PYTHON" -m venv' in text
    assert 'python3 -m venv "$SEARXNG_VENV"' not in text


def test_update_runs_venv_pin_migration():
    """Bestand wird bei jedem Update geprüft, nicht nur bei Neuinstallation."""
    text = (INSTALLER / "update.sh").read_text()

    assert "installer/migrations/pin-venv-python.sh" in text


def test_pin_migration_uses_build_version_and_is_idempotent():
    text = (INSTALLER / "migrations" / "pin-venv-python.sh").read_text()

    assert "pyvenv.cfg" in text                      # Bauversion statt fester Zahl
    assert '= "/usr/bin/python3" ] || continue' in text  # nur betroffene venvs
    assert '= "$built" ]' in text                    # läuft passend -> nichts tun
