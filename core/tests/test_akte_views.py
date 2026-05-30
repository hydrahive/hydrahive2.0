from __future__ import annotations

import pytest

from hydrahive.patientenakte import entities, patients, views


@pytest.fixture
def pid():
    p = patients.create("u1", {"slug": "alex"})
    entities.create("u1", p, "conditions", {"diagnose": "Diabetes", "diagnostiziert_am": "2021-05-01"})
    entities.create("u1", p, "events", {"typ": "OP", "datum_von": "2024-11-20", "einrichtung": "St. Katharinen"})
    entities.create("u1", p, "observations", {"parameter": "HbA1c", "wert": 6.4, "datum": "2026-05-01"})
    return p


def test_timeline_chronological_desc(pid):
    tl = views.timeline("u1", pid)
    dates = [e["sort_date"] for e in tl]
    assert dates == sorted(dates, reverse=True)   # neueste zuerst
    assert tl[0]["entity"] == "observations"      # 2026 oben


def test_timeline_entries_have_label_and_entity(pid):
    e = views.timeline("u1", pid)[0]
    assert "label" in e and "entity" in e and "record" in e


def test_summary_counts(pid):
    s = views.summary("u1", pid)
    assert s["conditions"] == 1
    assert s["events"] == 1
    assert s["observations"] == 1
    assert s.get("medications", 0) == 0


def test_views_foreign_patient_blocked():
    p = patients.create("u1", {"slug": "a"})
    with pytest.raises(PermissionError):
        views.summary("u2", p)
    with pytest.raises(PermissionError):
        views.timeline("u2", p)
