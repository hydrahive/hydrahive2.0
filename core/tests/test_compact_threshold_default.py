"""Tests für Issue #126: compact_threshold_pct Default 100 → 75."""
from __future__ import annotations

import json

import pytest

from hydrahive.agents._config_utils import normalize
from hydrahive.agents._defaults import DEFAULT_COMPACT_THRESHOLD_PCT


def test_default_ist_75():
    assert DEFAULT_COMPACT_THRESHOLD_PCT == 75


def test_normalize_setzt_default_bei_fehlendem_feld():
    cfg = {"id": "a1", "name": "test"}
    out = normalize(cfg)
    assert out["compact_threshold_pct"] == 75


def test_normalize_setzt_compact_max_turns_default_none():
    # None = window-skalierter Default im should_compact, kein fixer 1000er-Deckel.
    out = normalize({"id": "a1", "name": "test"})
    assert out["compact_max_turns"] is None


def test_normalize_respektiert_expliziten_user_wert():
    # User hat 100 gewählt → bleibt 100, Default greift nicht
    cfg = {"id": "a1", "name": "test", "compact_threshold_pct": 100}
    out = normalize(cfg)
    assert out["compact_threshold_pct"] == 100
    # Auch 50 bleibt
    cfg2 = {"id": "a2", "name": "test2", "compact_threshold_pct": 50}
    assert normalize(cfg2)["compact_threshold_pct"] == 50


def test_migrate_script_dry_run_aendert_nichts(setup_test_env, tmp_path, monkeypatch):
    """Dry-run darf nichts auf Disk schreiben."""
    from hydrahive.settings import settings

    monkeypatch.setattr(settings, "agents_dir", tmp_path)
    agent_dir = tmp_path / "agent-old"
    agent_dir.mkdir()
    cfg = {"id": "agent-old", "name": "old", "compact_threshold_pct": 100}
    (agent_dir / "config.json").write_text(json.dumps(cfg))

    from hydrahive.scripts import migrate_compact_threshold as mig
    rc = mig.main.__wrapped__() if hasattr(mig.main, "__wrapped__") else None  # noqa
    # main() parsed argv — wir testen die Kernlogik direkt
    import sys
    monkeypatch.setattr(sys, "argv", ["mig"])  # kein --apply
    rc = mig.main()
    assert rc == 0
    # Config noch unverändert
    saved = json.loads((agent_dir / "config.json").read_text())
    assert saved["compact_threshold_pct"] == 100


def test_migrate_script_apply_schreibt_neuen_wert(setup_test_env, tmp_path, monkeypatch):
    from hydrahive.settings import settings

    monkeypatch.setattr(settings, "agents_dir", tmp_path)
    agent_dir = tmp_path / "agent-old"
    agent_dir.mkdir()
    cfg = {"id": "agent-old", "name": "old", "compact_threshold_pct": 100}
    (agent_dir / "config.json").write_text(json.dumps(cfg))

    # Auch ein Agent der schon korrekt ist (75) — darf nicht angefasst werden
    agent_dir2 = tmp_path / "agent-ok"
    agent_dir2.mkdir()
    cfg2 = {"id": "agent-ok", "name": "ok", "compact_threshold_pct": 75}
    (agent_dir2 / "config.json").write_text(json.dumps(cfg2))

    # Auch ein Agent ohne das Feld — darf nicht angefasst werden (normalize handelt das)
    agent_dir3 = tmp_path / "agent-nofield"
    agent_dir3.mkdir()
    cfg3 = {"id": "agent-nofield", "name": "no"}
    (agent_dir3 / "config.json").write_text(json.dumps(cfg3))

    from hydrahive.scripts import migrate_compact_threshold as mig
    import sys
    monkeypatch.setattr(sys, "argv", ["mig", "--apply"])
    rc = mig.main()
    assert rc == 0

    # Nur agent-old muss geändert worden sein
    assert json.loads((agent_dir / "config.json").read_text())["compact_threshold_pct"] == 75
    assert json.loads((agent_dir2 / "config.json").read_text())["compact_threshold_pct"] == 75
    saved3 = json.loads((agent_dir3 / "config.json").read_text())
    assert "compact_threshold_pct" not in saved3  # raw config nicht normalisiert
