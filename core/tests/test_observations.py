"""Tests für Observations — Storage und Bulk-Update.

Mockt `_obs_file` per monkeypatch um tmp_path zu nutzen — keine Settings-Manipulation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydrahive.tools import _observations
from hydrahive.tools._observations import (
    list_raw_observations,
    mark_compressed,
    mark_compressed_bulk,
)


@pytest.fixture
def obs_path(tmp_path, monkeypatch):
    """Einzelne JSONL-Datei pro Test, _obs_file zeigt drauf."""
    target = tmp_path / "obs.jsonl"
    monkeypatch.setattr(_observations, "_obs_file", lambda a, s: target)
    return target


def _seed(path: Path, items: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in items) + "\n",
        encoding="utf-8",
    )


def test_bulk_kein_file_returns_0(obs_path):
    # File existiert nicht
    assert mark_compressed_bulk("a", "s", {"obs1": "cobs1"}) == 0


def test_bulk_leere_mappings_returns_0(obs_path):
    _seed(obs_path, [{"id": "obs1", "compressed": False}])
    assert mark_compressed_bulk("a", "s", {}) == 0


def test_bulk_aktualisiert_mehrere_in_einem_pass(obs_path):
    _seed(obs_path, [
        {"id": "obs1", "compressed": False, "tool_name": "x"},
        {"id": "obs2", "compressed": False, "tool_name": "y"},
        {"id": "obs3", "compressed": False, "tool_name": "z"},
    ])
    found = mark_compressed_bulk("a", "s", {"obs1": "cobs1", "obs3": "cobs3"})
    assert found == 2

    items = list_raw_observations("a", "s")
    by_id = {o["id"]: o for o in items}
    assert by_id["obs1"]["compressed"] is True
    assert by_id["obs1"]["compressed_id"] == "cobs1"
    assert by_id["obs2"]["compressed"] is False
    assert by_id["obs3"]["compressed"] is True
    assert by_id["obs3"]["compressed_id"] == "cobs3"


def test_bulk_unbekannte_ids_werden_ignoriert(obs_path):
    _seed(obs_path, [{"id": "obs1", "compressed": False}])
    found = mark_compressed_bulk("a", "s", {"obs1": "cobs1", "missing": "x"})
    assert found == 1


def test_bulk_alle_ids_unbekannt_keine_writes(obs_path):
    """Wenn nichts matched, soll kein File-Write passieren."""
    original = b'{"id":"obs1","compressed":false}\n'
    obs_path.write_bytes(original)
    found = mark_compressed_bulk("a", "s", {"missing": "x"})
    assert found == 0
    # File-Inhalt sollte byte-identisch sein (kein Re-Write)
    assert obs_path.read_bytes() == original


def test_bulk_kaputte_zeile_uebersprungen_nicht_gecrasht(obs_path):
    obs_path.write_text(
        '{"id":"obs1","compressed":false}\n'
        'NICHT_JSON\n'
        '{"id":"obs2","compressed":false}\n',
        encoding="utf-8",
    )
    found = mark_compressed_bulk("a", "s", {"obs1": "cobs1", "obs2": "cobs2"})
    assert found == 2
    # Kaputte Zeile bleibt erhalten
    raw = obs_path.read_text(encoding="utf-8")
    assert "NICHT_JSON" in raw


def test_single_mark_compressed_uses_bulk_returns_true_when_found(obs_path):
    _seed(obs_path, [{"id": "obs1", "compressed": False}])
    assert mark_compressed("a", "s", "obs1", "cobs1") is True


def test_single_mark_compressed_returns_false_when_missing(obs_path):
    _seed(obs_path, [{"id": "obs1", "compressed": False}])
    assert mark_compressed("a", "s", "missing", "cobs1") is False
