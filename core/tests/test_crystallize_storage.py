"""Tests für Crystallize-Storage — append-only Versioning + Re-Crystallize.

Mockt `_crystals_file` per monkeypatch um tmp_path zu nutzen.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydrahive.tools import _crystallize_storage
from hydrahive.tools._crystallize_storage import (
    Crystal,
    get_crystal,
    list_crystals,
    save_crystal,
)


@pytest.fixture
def crystals_path(tmp_path, monkeypatch):
    """Einzelne JSONL-Datei pro Test, _crystals_file zeigt drauf."""
    target = tmp_path / "crystals.jsonl"
    monkeypatch.setattr(_crystals_storage_lookup(), "_crystals_file", lambda a: target)
    return target


def _crystals_storage_lookup():
    return _crystallize_storage


def _seed(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n",
        encoding="utf-8",
    )


def _crystal(sid: str, *, project: str | None = None, narrative: str = "x") -> Crystal:
    return {
        "id": f"cry-{sid}-{narrative}",
        "session_id": sid,
        "agent_id": "a",
        "project": project,
        "created_at": "2026-05-09T00:00:00Z",
        "narrative": narrative,
        "key_outcomes": [],
        "files_affected": [],
        "lessons": [],
        "source_observation_ids": [],
        "observation_count": 0,
    }


# --- get_crystal: append-only, neueste gewinnt ---------------------------

def test_get_crystal_kein_file_returns_none(crystals_path):
    assert get_crystal("a", "s1") is None


def test_get_crystal_einzelner_eintrag(crystals_path):
    _seed(crystals_path, [_crystal("s1", narrative="v1")])
    result = get_crystal("a", "s1")
    assert result is not None
    assert result["narrative"] == "v1"


def test_get_crystal_mehrere_versionen_gibt_neueste(crystals_path):
    _seed(crystals_path, [
        _crystal("s1", narrative="v1"),
        _crystal("s1", narrative="v2"),
        _crystal("s1", narrative="v3"),
    ])
    result = get_crystal("a", "s1")
    assert result is not None
    assert result["narrative"] == "v3"


def test_get_crystal_andere_session_unbeeinflusst(crystals_path):
    _seed(crystals_path, [
        _crystal("s1", narrative="v1"),
        _crystal("s2", narrative="other"),
        _crystal("s1", narrative="v2"),
    ])
    assert get_crystal("a", "s1")["narrative"] == "v2"
    assert get_crystal("a", "s2")["narrative"] == "other"


def test_get_crystal_ueberspringt_kaputte_zeile(crystals_path):
    crystals_path.parent.mkdir(parents=True, exist_ok=True)
    crystals_path.write_text(
        json.dumps(_crystal("s1", narrative="ok")) + "\n"
        "NICHT_JSON\n"
        + json.dumps(_crystal("s1", narrative="latest")) + "\n",
        encoding="utf-8",
    )
    assert get_crystal("a", "s1")["narrative"] == "latest"


# --- list_crystals: dedup per session_id, neueste pro Session ------------

def test_list_crystals_dedup_per_session(crystals_path):
    _seed(crystals_path, [
        _crystal("s1", narrative="v1"),
        _crystal("s2", narrative="x"),
        _crystal("s1", narrative="v2"),
        _crystal("s1", narrative="v3"),
    ])
    results = list_crystals("a")
    assert len(results) == 2
    by_sid = {r["session_id"]: r for r in results}
    assert by_sid["s1"]["narrative"] == "v3"
    assert by_sid["s2"]["narrative"] == "x"


def test_list_crystals_neueste_zuerst(crystals_path):
    _seed(crystals_path, [
        _crystal("s1", narrative="alt"),
        _crystal("s2", narrative="neu"),
    ])
    results = list_crystals("a")
    assert results[0]["session_id"] == "s2"
    assert results[1]["session_id"] == "s1"


def test_list_crystals_project_filter(crystals_path):
    _seed(crystals_path, [
        _crystal("s1", project="p1"),
        _crystal("s2", project="p2"),
        _crystal("s3", project=None),
    ])
    p1_results = list_crystals("a", project="p1")
    assert len(p1_results) == 1
    assert p1_results[0]["session_id"] == "s1"


def test_list_crystals_limit(crystals_path):
    _seed(crystals_path, [_crystal(f"s{i}") for i in range(5)])
    results = list_crystals("a", limit=2)
    assert len(results) == 2


def test_list_crystals_dedup_dann_limit(crystals_path):
    """Bei 3 Versionen von s1 + s2 + s3 mit limit=2 sollen 2 unique Sessions kommen."""
    _seed(crystals_path, [
        _crystal("s1", narrative="v1"),
        _crystal("s1", narrative="v2"),
        _crystal("s1", narrative="v3"),
        _crystal("s2"),
        _crystal("s3"),
    ])
    results = list_crystals("a", limit=2)
    assert len(results) == 2
    sids = [r["session_id"] for r in results]
    assert "s1" not in sids or sids.count("s1") == 1


# --- save_crystal: append-only ------------------------------------------

def test_save_crystal_appended(crystals_path):
    save_crystal("a", _crystal("s1", narrative="v1"))
    save_crystal("a", _crystal("s1", narrative="v2"))
    lines = crystals_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert get_crystal("a", "s1")["narrative"] == "v2"
