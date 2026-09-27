"""/model im Chat wirkt wie der Modell-Picker: nur auf die Session (MED-6).

Vorher änderte /model per agentsApi.update das Standardmodell des Agenten für
ALLE Sessions, während der Picker links nur die Session umstellte.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _model_cmd() -> str:
    src = (ROOT / "frontend/src/features/chat/commands.ts").read_text(encoding="utf-8")
    start = src.index("async function modelCmd(")
    return src[start:src.index("\n}\n", start)]


def test_model_befehl_setzt_session_override():
    body = _model_cmd()
    assert "chatApi.updateSession(session.id, { model_override: target })" in body
    assert "agentsApi.update" not in body


def test_model_default_hebt_override_auf():
    assert '{ model_override: "" }' in _model_cmd()


def test_hilfetext_nennt_session():
    src = (ROOT / "frontend/src/features/chat/commands.ts").read_text(encoding="utf-8")
    assert "für diese Session wechseln" in src
