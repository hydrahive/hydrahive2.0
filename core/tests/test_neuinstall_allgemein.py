"""Nichts nur auf unseren Server gebaut (Befund 23.11.2026 vor einer fremden Neuinstallation).

- Health-Ingest-Nutzer hatte den Standard 'till'.
- ask_agent verlangte für Projektarbeit IMMER ein Zieldokument (unsere Arbeitsweise) und nannte dabei „Till“.
- Beispiele „projektx-till“ in Werkzeug-Schema und Oberfläche.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.settings import overrides
from hydrahive.settings.editable import BY_KEY
from hydrahive.tools import _ask_agent_anchor as anchor

REPO = Path(__file__).resolve().parents[2]


def _fresh_settings():
    from hydrahive.settings.settings import Settings
    return Settings()


def test_health_ingest_user_ohne_standard(monkeypatch):
    monkeypatch.delenv("HH_HEALTH_INGEST_USER", raising=False)
    monkeypatch.setattr(overrides, "get_overrides", lambda: {})
    assert _fresh_settings().health_ingest_user == ""


def test_health_ingest_user_aus_oberflaeche(monkeypatch):
    monkeypatch.delenv("HH_HEALTH_INGEST_USER", raising=False)
    monkeypatch.setattr(overrides, "get_overrides", lambda: {"health_ingest_user": " bibs "})
    assert _fresh_settings().health_ingest_user == "bibs"
    assert BY_KEY["health_ingest_user"].env_var == "HH_HEALTH_INGEST_USER"


def test_health_ingest_user_aus_umgebung_bleibt(monkeypatch):
    monkeypatch.setenv("HH_HEALTH_INGEST_USER", "till")
    monkeypatch.setattr(overrides, "get_overrides", lambda: {})
    assert _fresh_settings().health_ingest_user == "till"


@pytest.mark.parametrize("value,expected", [(None, False), ("0", False), ("1", True), ("true", True),
                                            ("on", True), ("nein", False)])
def test_ziel_pflicht_ist_einstellung_standard_aus(monkeypatch, value, expected):
    monkeypatch.delenv("HH_AGENT_GOAL_REQUIRED", raising=False)
    monkeypatch.setattr(overrides, "get_overrides", lambda: {} if value is None else {"agent_goal_required": value})
    assert anchor.goal_required() is expected
    assert BY_KEY["agent_goal_required"].default == "0" and BY_KEY["agent_goal_required"].type == "bool"


def test_kein_till_in_texten_fuer_agenten_und_oberflaeche():
    for rel in ("core/src/hydrahive/tools/_ask_agent_anchor.py", "core/src/hydrahive/tools/_ask_agent_schema.py",
                "frontend/src/features/federation/_AddDialog.tsx"):
        text = (REPO / rel).read_text(encoding="utf-8")
        strings = [line for line in text.splitlines() if '"' in line and not line.lstrip().startswith(("#", "//"))]
        assert not any("Till" in s or "-till" in s for s in strings), rel


def test_kein_standard_till_in_settings():
    text = (REPO / "core/src/hydrahive/settings/_services.py").read_text(encoding="utf-8")
    assert '"till"' not in text
