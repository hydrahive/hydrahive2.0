"""Regression: Modul-Build verwirft den inkrementellen TypeScript-Cache.

Hintergrund (Testserver, 2026-08-19): Nach der Installation von 17 Modulen
fehlten im Cockpit fast alle Einträge. Ursache war nicht die Installation
selbst — die Dateien lagen korrekt auf der Platte —, sondern der Build danach:

    error TS6053: File '…/src/modules/haushaltsbuch/index.tsx' not found.

Die Datei existierte. ``tsc -b`` arbeitet inkrementell und hält seinen Zustand
in ``node_modules/.tmp/*.tsbuildinfo``. Der Cache stammte noch aus einem Lauf
ohne diese Module, der Build brach ab, und ``dist/`` blieb auf dem alten Stand.
Backend meldete 17 installierte Module, das ausgelieferte Frontend kannte
keines davon.
"""

from __future__ import annotations

from pathlib import Path


def test_clear_ts_buildinfo_removes_stale_cache(tmp_path: Path):
    from hydrahive.modules.installer import _clear_ts_buildinfo

    tmp_dir = tmp_path / "node_modules" / ".tmp"
    tmp_dir.mkdir(parents=True)
    app = tmp_dir / "tsconfig.app.tsbuildinfo"
    node = tmp_dir / "tsconfig.node.tsbuildinfo"
    keep = tmp_dir / "something-else.json"
    for f in (app, node, keep):
        f.write_text("x")

    _clear_ts_buildinfo(tmp_path)

    assert not app.exists(), "stale tsbuildinfo muss geloescht werden"
    assert not node.exists(), "stale tsbuildinfo muss geloescht werden"
    assert keep.exists(), "fremde Dateien duerfen nicht angefasst werden"


def test_clear_ts_buildinfo_tolerates_missing_dir(tmp_path: Path):
    """Frischer Checkout ohne node_modules darf nicht knallen."""
    from hydrahive.modules.installer import _clear_ts_buildinfo

    _clear_ts_buildinfo(tmp_path)   # kein Raise erwartet


def test_frontend_build_clears_cache_before_npm(tmp_path: Path, monkeypatch):
    """Die Reihenfolge ist entscheidend: erst Cache weg, dann bauen."""
    from hydrahive.modules import installer

    tmp_dir = tmp_path / "frontend" / "node_modules" / ".tmp"
    tmp_dir.mkdir(parents=True)
    stale = tmp_dir / "tsconfig.app.tsbuildinfo"
    stale.write_text("x")

    calls: list[str] = []

    class _FakeSettings:
        base_dir = tmp_path

    def _fake_run(cmd, **kwargs):
        # Zum Zeitpunkt des Builds darf der Cache nicht mehr existieren.
        calls.append("cache-weg" if not stale.exists() else "cache-noch-da")
        return None

    monkeypatch.setattr(installer, "settings", _FakeSettings)
    monkeypatch.setattr(installer.subprocess, "run", _fake_run)

    installer._frontend_build()

    assert calls == ["cache-weg"]
