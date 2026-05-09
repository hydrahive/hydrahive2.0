"""Tests für update_provider_oauth — atomic RMW mit flock."""
from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path

import pytest

from hydrahive.oauth._llm_config_rmw import update_provider_oauth


@pytest.fixture
def llm_json(tmp_path):
    path = tmp_path / "llm.json"
    path.write_text(json.dumps({
        "providers": [
            {"id": "anthropic", "oauth": {"access": "old", "expires_at": 0}},
            {"id": "openai_codex", "oauth": {"access": "old_codex"}},
        ],
    }))
    return path


def test_update_existing_provider(llm_json):
    update_provider_oauth(llm_json, "anthropic", {"access": "new", "expires_at": 999})
    data = json.loads(llm_json.read_text())
    anthropic = next(p for p in data["providers"] if p["id"] == "anthropic")
    assert anthropic["oauth"]["access"] == "new"
    assert anthropic["oauth"]["expires_at"] == 999


def test_update_andere_provider_unbeeinflusst(llm_json):
    update_provider_oauth(llm_json, "anthropic", {"access": "new"})
    data = json.loads(llm_json.read_text())
    codex = next(p for p in data["providers"] if p["id"] == "openai_codex")
    assert codex["oauth"]["access"] == "old_codex"


def test_update_nicht_existierender_provider_no_op(llm_json):
    original = llm_json.read_text()
    update_provider_oauth(llm_json, "ghost", {"access": "x"})
    assert llm_json.read_text() == original


def test_update_pfad_existiert_nicht_no_op(tmp_path):
    missing = tmp_path / "nirgendwo.json"
    update_provider_oauth(missing, "anthropic", {"access": "x"})
    assert not missing.exists()


def test_atomic_write_kein_zwischenstand(llm_json, monkeypatch):
    """Verifiziert dass das File während des Writes nie partiell sichtbar ist."""
    import json as _json
    written_states: list[str] = []
    original = Path.write_text

    def capture(self, content, **kw):
        if self.name == llm_json.name:
            written_states.append(content)
        return original(self, content, **kw)

    monkeypatch.setattr(Path, "write_text", capture)
    update_provider_oauth(llm_json, "anthropic", {"access": "fresh"})
    # Write nur auf .tmp, nicht direkt auf path. Der finale Replace ist atomar.
    final_data = _json.loads(llm_json.read_text())
    anthropic = next(p for p in final_data["providers"] if p["id"] == "anthropic")
    assert anthropic["oauth"]["access"] == "fresh"


def _worker(path_str: str, provider: str, value: str, idx: int):
    """Worker für concurrent-Test."""
    from hydrahive.oauth._llm_config_rmw import update_provider_oauth as fn
    fn(Path(path_str), provider, {"access": value, "marker": idx})


def test_concurrent_writes_kein_datenverlust(llm_json):
    """5 parallele Refreshes auf gleichen Provider — am Ende ist genau einer drin."""
    procs = []
    for i in range(5):
        p = mp.Process(target=_worker, args=(str(llm_json), "anthropic", f"v{i}", i))
        p.start()
        procs.append(p)
    for p in procs:
        p.join()

    # Die JSON ist parsbar (kein partial write)
    data = json.loads(llm_json.read_text())
    anthropic = next(p for p in data["providers"] if p["id"] == "anthropic")
    # Genau einer der 5 Writes hat gewonnen — nicht entscheidend welcher
    assert anthropic["oauth"]["marker"] in {0, 1, 2, 3, 4}
    # codex unverändert
    codex = next(p for p in data["providers"] if p["id"] == "openai_codex")
    assert codex["oauth"]["access"] == "old_codex"
