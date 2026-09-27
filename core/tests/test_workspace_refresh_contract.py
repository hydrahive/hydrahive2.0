"""Dateibaum aktualisiert sich nach Agent-Läufen und per Knopf (MED-7).

Vorher lud FileTree nur bei Wechsel von Agent/Pfad; neue Dateien des Agenten
erschienen erst nach Seiten-Reload.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "frontend/src"


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_stream_meldet_laufende():
    src = _read("features/chat/_chatStream.ts")
    done = src[src.index('ev.type === "done"'):]
    assert "notifyRunFinished()" in done[:600]
    err = src[src.index('ev.type === "error"'):]
    assert "notifyRunFinished()" in err[:600]


def test_signal_modul_hat_event_und_hook():
    src = _read("shared/runFinished.ts")
    assert "hh-run-finished" in src
    assert "export function notifyRunFinished" in src
    assert "export function useRunFinished" in src
    assert "removeEventListener" in src


def test_chat_dateibaum_hat_knopf_und_hoert_auf_laufende():
    panel = _read("features/chat/workspace/WorkspacePanel.tsx")
    assert "useRunFinished" in panel
    assert "RefreshCw" in panel
    assert "key={`files-${treeRevision}`}" in panel


def test_projekt_dateimanager_hat_knopf_und_hoert_auf_laufende():
    panel = _read("features/cockpit/project/ProjectWorkspacePanel.tsx")
    assert "useRunFinished(reload)" in panel
    assert "RefreshCw" in panel
