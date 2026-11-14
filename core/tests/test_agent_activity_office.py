"""Erweiterte Activity-Registry fürs Agenten-Büro (Spec agent-office.md §1)."""
from __future__ import annotations

import time

from hydrahive.runner import activity


def _agent():
    return {"id": "a1", "name": "Reviewer"}


def test_start_mit_zusatzfeldern():
    activity.stop("o1")
    activity.start("o1", _agent(), owner="u", project_id="P",
                   parent_session_id="eltern-1", delegation_id="d1",
                   max_iterations=40, deadline_at=time.time() + 300)
    snap = activity.snapshot("u")
    row = next(e for e in snap if e["session_id"] == "o1")
    assert row["parent_session_id"] == "eltern-1"
    assert row["delegation_id"] == "d1"
    assert row["iteration"] == 0 and row["max_iterations"] == 40
    assert row["deadline_at"] is not None
    assert row["last_tool_result_summary"] == ""
    activity.stop("o1")


def test_start_ohne_zusatzfelder_bleibt_abwaertskompatibel():
    activity.stop("o2")
    activity.start("o2", _agent(), owner="u", project_id=None)
    row = next(e for e in activity.snapshot("u") if e["session_id"] == "o2")
    assert row["parent_session_id"] is None and row["delegation_id"] is None
    assert row["iteration"] == 0 and row["max_iterations"] == 0 and row["deadline_at"] is None
    activity.stop("o2")


def test_set_tool_erhoeht_iteration_und_setzt_zusammenfassung():
    activity.stop("o3")
    activity.start("o3", _agent(), owner="u", project_id=None)
    activity.set_tool("o3", "shell_exec", result_summary="Exit 0, 3 Dateien geändert" * 10)
    row = activity.snapshot("u")[0]
    assert row["current_tool"] == "shell_exec" and row["iteration"] == 1
    assert len(row["last_tool_result_summary"]) <= 120
    activity.set_tool("o3", "file_read", result_summary="kurz")
    row = activity.snapshot("u")[0]
    assert row["iteration"] == 2 and row["last_tool_result_summary"] == "kurz"
    activity.stop("o3")


def test_set_tool_ohne_zusammenfassung_behaelt_vorherige():
    activity.stop("o4")
    activity.start("o4", _agent(), owner="u", project_id=None)
    activity.set_tool("o4", "web_search", result_summary="erster Fund")
    activity.set_tool("o4", "fetch_url")   # kein result_summary → zeigt weiter "erster Fund", bis das nächste da ist
    assert activity.snapshot("u")[0]["last_tool_result_summary"] == "erster Fund"
    activity.stop("o4")
