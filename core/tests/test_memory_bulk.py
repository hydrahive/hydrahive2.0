"""Tests für write_keys_bulk — Single read+write pro Batch."""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.tools import _memory_io
from hydrahive.tools._memory_io import (
    load,
    write_key,
    write_keys_bulk,
)


@pytest.fixture
def memory_path(tmp_path, monkeypatch):
    target = tmp_path / "agents" / "a" / "memory.json"
    monkeypatch.setattr(_memory_io, "_memory_file", lambda agent_id: target)
    return target


def test_bulk_leere_liste_kein_write(memory_path):
    assert write_keys_bulk("a", []) == []
    assert not memory_path.exists()


def test_bulk_schreibt_alle_eintraege(memory_path):
    results = write_keys_bulk("a", [
        {"key": "k1", "content": "v1"},
        {"key": "k2", "content": "v2"},
        {"key": "k3", "content": "v3"},
    ])
    assert len(results) == 3
    data = load("a")
    assert data["k1"]["content"] == "v1"
    assert data["k2"]["content"] == "v2"
    assert data["k3"]["content"] == "v3"


def test_bulk_ein_einziger_file_write(memory_path, monkeypatch):
    """Verifiziert: write_keys_bulk macht 1× save für N Einträge."""
    save_calls = []
    original_save = _memory_io.save
    monkeypatch.setattr(_memory_io, "save", lambda *a, **kw: save_calls.append(1) or original_save(*a, **kw))

    write_keys_bulk("a", [
        {"key": f"k{i}", "content": f"v{i}"} for i in range(10)
    ])
    assert len(save_calls) == 1


def test_bulk_vs_single_loop_save_count(memory_path, monkeypatch):
    """Vergleichs-Test: 5×write_key = 5 saves, 1×write_keys_bulk = 1 save."""
    save_calls = []
    original_save = _memory_io.save
    monkeypatch.setattr(_memory_io, "save", lambda *a, **kw: save_calls.append(1) or original_save(*a, **kw))

    for i in range(5):
        write_key("a", f"single{i}", f"v{i}")
    single_saves = len(save_calls)
    save_calls.clear()

    write_keys_bulk("a", [
        {"key": f"bulk{i}", "content": f"v{i}"} for i in range(5)
    ])
    bulk_saves = len(save_calls)

    assert single_saves == 5
    assert bulk_saves == 1


def test_bulk_uebernimmt_optionale_felder(memory_path):
    write_keys_bulk("a", [
        {"key": "k1", "content": "x", "confidence": 0.9, "project": "p1"},
        {"key": "k2", "content": "y", "confidence": 0.3, "project": None},
    ])
    data = load("a")
    assert data["k1"]["confidence"] == 0.9
    assert data["k1"]["project"] == "p1"
    assert data["k2"]["confidence"] == 0.3
    assert data["k2"]["project"] is None


def test_bulk_check_contradictions_default_true(memory_path, monkeypatch):
    """Verifiziert dass check_contradictions=True (default) durchgereicht wird."""
    calls: list[bool] = []
    from hydrahive.tools import _memory_io

    original = _memory_io._apply_write

    def spy(data, key, content, **kw):
        calls.append(kw.get("check_contradictions", True))
        return original(data, key, content, **kw)

    monkeypatch.setattr(_memory_io, "_apply_write", spy)
    write_keys_bulk("a", [{"key": "k1", "content": "x"}])
    assert calls == [True]


def test_bulk_check_contradictions_false_pro_eintrag(memory_path):
    """Lessons-Use-Case: check_contradictions=False überall."""
    write_keys_bulk("a", [
        {"key": "lesson.1", "content": "Test A", "check_contradictions": False},
        {"key": "lesson.2", "content": "Test B", "check_contradictions": False},
    ])
    data = load("a")
    assert "lesson.1" in data
    assert "lesson.2" in data
    assert data["lesson.1"]["is_latest"] is True
    assert data["lesson.2"]["is_latest"] is True


def test_bulk_update_bestehender_keys(memory_path):
    write_key("a", "k1", "alt")
    write_keys_bulk("a", [
        {"key": "k1", "content": "neu", "check_contradictions": False},
        {"key": "k2", "content": "x"},
    ])
    data = load("a")
    assert data["k1"]["content"] == "neu"
    assert data["k1"]["reinforcements"] >= 1
    assert data["k2"]["content"] == "x"


def test_bulk_returns_entry_und_superseded_in_order(memory_path):
    results = write_keys_bulk("a", [
        {"key": "k1", "content": "v1", "check_contradictions": False},
        {"key": "k2", "content": "v2", "check_contradictions": False},
    ])
    assert len(results) == 2
    entry1, sup1 = results[0]
    entry2, sup2 = results[1]
    assert entry1["content"] == "v1"
    assert entry2["content"] == "v2"
    assert sup1 == []
    assert sup2 == []
