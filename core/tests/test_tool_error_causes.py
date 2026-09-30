"""Tools melden die Ursache abgefangener Fehler (Task a0a8486d, Teil A).

13 Stellen in 8 Tools fingen `except Exception as e` und meldeten nur str(e).
Bei TimeoutError ist das leer: datamining_search meldete 55-mal nur
„Datamining-Suche fehlgeschlagen:“. Jetzt stehen Typ und Text in der Meldung,
bei Zeitüberschreitung ein Hinweis, und der Traceback geht ins Log.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest

from hydrahive.tools._errors import fail_with_cause
from hydrahive.tools.base import ToolContext


def _ctx(tmp_path: Path) -> ToolContext:
    return ToolContext(session_id="s-err", agent_id="a-err", user_id="u-err", workspace=tmp_path)


# ── Helfer ────────────────────────────────────────────────────────────────

def test_leere_meldung_bekommt_den_typ(tmp_path):
    r = fail_with_cause("Datamining-Suche fehlgeschlagen", RuntimeError(), "datamining_search")
    assert not r.success
    assert r.error == "Datamining-Suche fehlgeschlagen: RuntimeError"


def test_meldung_mit_text_behaelt_den_text(tmp_path):
    r = fail_with_cause("Schreibfehler", PermissionError(13, "Permission denied"), "file_write")
    assert r.error.startswith("Schreibfehler: PermissionError: ")
    assert "Permission denied" in r.error


@pytest.mark.parametrize("exc", [TimeoutError(), asyncio.TimeoutError()])
def test_zeitueberschreitung_wird_benannt(exc):
    r = fail_with_cause("Datamining-Suche fehlgeschlagen", exc, "datamining_search",
                        hint="Suchbegriff eingrenzen oder from_date setzen.")
    assert r.error.startswith("Datamining-Suche fehlgeschlagen: Zeitüberschreitung (TimeoutError)")
    assert r.error.endswith("Suchbegriff eingrenzen oder from_date setzen.")


def test_hinweis_nur_bei_zeitueberschreitung():
    r = fail_with_cause("X", ValueError("kaputt"), "t", hint="Suchbegriff eingrenzen.")
    assert r.error == "X: ValueError: kaputt"


def test_traceback_landet_im_log(caplog):
    caplog.set_level(logging.WARNING, logger="hydrahive.tools._errors")
    try:
        raise KeyError("fehlt")
    except KeyError as e:
        fail_with_cause("Anlegen fehlgeschlagen", e, "create_specialist")
    rec = [r for r in caplog.records if r.name == "hydrahive.tools._errors"]
    assert rec and rec[0].exc_info is not None
    assert "create_specialist" in rec[0].getMessage()


# ── Echte Tools ───────────────────────────────────────────────────────────

def _boom_timeout(*a, **kw):
    raise TimeoutError()


@pytest.mark.parametrize(("tool_attr", "func", "prefix"), [
    ("TOOL_SEARCH", "search_events", "Datamining-Suche fehlgeschlagen"),
    ("TOOL_SEMANTIC", "search_events", "Semantische Suche fehlgeschlagen"),
    ("TOOL_TIMELINE", "list_sessions", "Timeline-Abfrage fehlgeschlagen"),
    ("TOOL_TODAY", "list_sessions", "Today-Abfrage fehlgeschlagen"),
])
def test_datamining_zeigt_zeitueberschreitung(tool_attr, func, prefix, tmp_path, monkeypatch):
    from hydrahive.db import mirror_query
    from hydrahive.tools import datamining

    async def _slow(*a, **kw):
        raise TimeoutError()

    monkeypatch.setattr(mirror_query, func, _slow)
    tool = getattr(datamining, tool_attr)
    r = asyncio.run(tool.execute({"query": "x"}, _ctx(tmp_path)))
    assert not r.success
    assert r.error.startswith(f"{prefix}: Zeitüberschreitung (TimeoutError)")
    assert r.error.strip() != f"{prefix}:"
    # Ein Hinweis darf nur Parameter nennen, die das Tool wirklich hat.
    params = set(tool.schema.get("properties", {}))
    for name in ("from_date", "to_date", "limit"):
        if name in r.error:
            assert name in params, f"{tool.name}: Hinweis nennt {name}, Schema hat es nicht"


def test_file_write_nennt_den_typ(tmp_path, monkeypatch):
    from hydrahive.tools import file_write

    def _deny(self, *a, **kw):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "write_text", _deny)
    r = asyncio.run(file_write.TOOL.execute({"path": "a.txt", "content": "x"}, _ctx(tmp_path)))
    assert r.error.startswith("Schreibfehler: PermissionError:")


def test_file_read_nennt_den_typ(tmp_path, monkeypatch):
    from hydrahive.tools import file_read
    (tmp_path / "a.txt").write_text("x")

    def _deny(self, *a, **kw):
        raise OSError()

    monkeypatch.setattr(Path, "read_text", _deny)
    r = asyncio.run(file_read.TOOL.execute({"path": "a.txt"}, _ctx(tmp_path)))
    assert r.error == "Lesefehler: OSError"


@pytest.mark.parametrize("step", ["read", "write"])
def test_file_patch_nennt_den_typ(step, tmp_path, monkeypatch):
    from hydrahive.tools import file_patch
    (tmp_path / "a.txt").write_text("alt")
    target = "read_text" if step == "read" else "write_text"
    real = getattr(Path, target)

    def _deny(self, *a, **kw):
        if self.name == "a.txt":
            raise OSError()
        return real(self, *a, **kw)

    monkeypatch.setattr(Path, target, _deny)
    r = asyncio.run(file_patch.TOOL.execute({"path": "a.txt", "old_string": "alt", "new_string": "neu"}, _ctx(tmp_path)))
    assert r.error == ("Lesefehler: OSError" if step == "read" else "Schreibfehler: OSError")
