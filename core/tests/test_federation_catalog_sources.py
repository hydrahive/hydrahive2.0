"""Q1 — Föderations-Katalog Etappe 2: Katalog-Quellen in ModuleContext
(docs/specs/federation-catalog.md §Katalog-Quellen).

Anmeldung, doppelte Anmeldung, Registry je kind, und: catalog_changed kehrt
sofort zurück, wirft nie und tut ohne Sync/Hub/Nutzerauswahl nichts.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from hydrahive.federation import catalog_changes
from hydrahive.modules import catalog_sources
from hydrahive.modules.context import CatalogSource, ModuleContext
from hydrahive.modules.manifest import ModuleManifest
from hydrahive.modules.registry import LoadedModule


def _fns():
    return dict(
        list_changed=lambda username, after, limit: [],
        list_versions=lambda username: [],
        get_full=lambda username, item_id: None,
        query=lambda usernames, project, status, q, limit, offset: [],
    )


def _broken_fns():
    def boom(*a, **k):
        raise RuntimeError("kaputte Quelle")
    return dict(list_changed=boom, list_versions=boom, get_full=boom, query=boom)


def _loaded(mid: str, ctx: ModuleContext, loaded: bool = True) -> LoadedModule:
    return LoadedModule(
        name=mid, manifest=ModuleManifest(id=mid, name=mid, version="1.0.0"),
        path=Path("."), ctx=ctx, loaded=loaded,
    )


@pytest.fixture(autouse=True)
def _reset_state():
    snap = dict(catalog_sources.CATALOG_SOURCES)
    catalog_changes._reset_for_tests()
    yield
    catalog_changes._reset_for_tests()
    catalog_sources.CATALOG_SOURCES.clear()
    catalog_sources.CATALOG_SOURCES.update(snap)


def _open_gate(users=("till",)):
    catalog_changes._gate = catalog_changes._Gate(active=True, users=frozenset(users))


# --- Anmeldung ---------------------------------------------------------------

def test_register_catalog_source_speichert_quelle():
    ctx = ModuleContext("tasks")
    fns = _fns()
    ctx.register_catalog_source("task", **fns)
    assert len(ctx.catalog_sources) == 1
    src = ctx.catalog_sources[0]
    assert isinstance(src, CatalogSource)
    assert src.kind == "task"
    assert src.list_changed is fns["list_changed"]
    assert src.query is fns["query"]


def test_register_catalog_source_positionsgebunden():
    """Spec-Reihenfolge: kind, list_changed, list_versions, get_full, query."""
    ctx = ModuleContext("scratchpad")
    f = _fns()
    ctx.register_catalog_source("idea", f["list_changed"], f["list_versions"], f["get_full"], f["query"])
    assert ctx.catalog_sources[0].get_full is f["get_full"]


def test_doppelte_anmeldung_im_selben_modul_uebersprungen(caplog):
    """Wirft nicht (Modul bleibt geladen), erste Quelle gilt, Warnung im Log."""
    ctx = ModuleContext("tasks")
    first = _fns()
    assert ctx.register_catalog_source("task", **first) is True
    assert ctx.register_catalog_source("task", **_fns()) is False
    assert len(ctx.catalog_sources) == 1
    assert ctx.catalog_sources[0].list_changed is first["list_changed"]
    assert "schon angemeldet" in caplog.text


def test_unbekannte_art_uebersprungen():
    ctx = ModuleContext("x")
    assert ctx.register_catalog_source("note", **_fns()) is False
    assert ctx.catalog_sources == []


def test_nicht_aufrufbare_funktion_uebersprungen():
    ctx = ModuleContext("x")
    fns = _fns()
    fns["get_full"] = None
    assert ctx.register_catalog_source("task", **fns) is False
    assert ctx.catalog_sources == []


def test_ungueltige_anmeldung_bricht_modul_laden_nicht(tmp_path, monkeypatch):
    """Ein Fehler bei der Anmeldung darf das Modul (Router/Tools/Jobs) nicht kippen."""
    from hydrahive.modules import loader

    mod = tmp_path / "katmod"
    (mod / "backend").mkdir(parents=True)
    (mod / "manifest.json").write_text('{"id": "katmod", "name": "katmod", "version": "1.0.0"}')
    (mod / "backend" / "__init__.py").write_text(
        "def register(ctx):\n"
        "    f = lambda *a: []\n"
        "    ctx.register_catalog_source('ticket', f, f, f, f)\n"
        "    ctx.register_catalog_source('task', f, f, f, f)\n"
        "    ctx.register_catalog_source('task', f, f, f, f)\n"
    )
    monkeypatch.setattr(loader, "ensure_module_templates", lambda *a, **k: None)
    loaded = loader._load_one(mod)
    assert loaded.loaded is True, loaded.error
    assert [s.kind for s in loaded.ctx.catalog_sources] == ["task"]


# --- Registry im Kern: je kind höchstens eine Quelle -------------------------

def test_registry_je_kind_hoechstens_eine_quelle(monkeypatch):
    a, b, c = ModuleContext("tasks"), ModuleContext("tasks2"), ModuleContext("scratchpad")
    a.register_catalog_source("task", **_fns())
    b.register_catalog_source("task", **_fns())
    c.register_catalog_source("idea", **_fns())
    monkeypatch.setattr(catalog_sources, "REGISTRY", {
        "tasks": _loaded("tasks", a), "tasks2": _loaded("tasks2", b), "scratchpad": _loaded("scratchpad", c),
    })
    assert catalog_sources.collect_catalog_sources() == 2
    assert catalog_sources.CATALOG_SOURCES["task"][0] == "tasks"
    assert catalog_sources.get_source("task") is a.catalog_sources[0]
    assert catalog_sources.source_kinds() == ["idea", "task"]


def test_registry_ignoriert_nicht_geladene_module(monkeypatch):
    ctx = ModuleContext("tasks")
    ctx.register_catalog_source("task", **_fns())
    monkeypatch.setattr(catalog_sources, "REGISTRY", {"tasks": _loaded("tasks", ctx, loaded=False)})
    assert catalog_sources.collect_catalog_sources() == 0
    assert catalog_sources.get_source("task") is None


# --- catalog_changed: sofort, wirft nie, ohne Hub nichts ----------------------

def test_catalog_changed_ohne_hub_tut_nichts():
    ctx = ModuleContext("tasks")
    ctx.register_catalog_source("task", **_fns())
    assert ctx.catalog_changed("task", "till", "t-1") is None
    assert catalog_changes.pending_count() == 0
    assert not catalog_changes.is_dirty()


def test_catalog_changed_merkt_vor_wenn_aktiv():
    _open_gate()
    ctx = ModuleContext("tasks")
    for _ in range(5):  # fünf Schreibvorgänge desselben Eintrags → eine Vormerkung
        ctx.catalog_changed("task", "till", "t-1")
    ctx.catalog_changed("idea", "till", "i-1")
    assert catalog_changes.is_dirty()
    items, overflow = catalog_changes.drain()
    assert items == [("idea", "till", "i-1"), ("task", "till", "t-1")]
    assert overflow is False
    assert catalog_changes.pending_count() == 0


def test_catalog_changed_nicht_ausgewaehlter_nutzer_ignoriert():
    _open_gate(users=("till",))
    ModuleContext("tasks").catalog_changed("task", "anna", "t-1")
    assert catalog_changes.pending_count() == 0


@pytest.mark.parametrize("args", [
    ("task", None, "t-1"), ("task", "till", None), ("task", "till", ""),
    (None, "till", "t-1"), ("note", "till", "t-1"), (123, ["x"], {"y": 1}),
])
def test_catalog_changed_wirft_nie_bei_falschen_werten(args):
    _open_gate()
    ModuleContext("tasks").catalog_changed(*args)
    assert catalog_changes.pending_count() == 0


def test_catalog_changed_wirft_nie_bei_kaputter_quelle_und_kaputtem_kern(monkeypatch):
    ctx = ModuleContext("tasks")
    ctx.register_catalog_source("task", **_broken_fns())
    _open_gate()
    ctx.catalog_changed("task", "till", "t-1")  # Quelle wird nicht aufgerufen

    def explode(*a, **k):
        raise RuntimeError("Kern kaputt")
    monkeypatch.setattr(catalog_changes, "mark_changed", explode)
    assert ctx.catalog_changed("task", "till", "t-2") is None


def test_catalog_changed_ohne_datenbank_und_schnell(monkeypatch):
    """Keine I/O im Schreibpfad: auch mit kaputter DB-Verbindung sofort zurück."""
    from hydrahive.db import connection

    def no_db(*a, **k):
        raise AssertionError("catalog_changed darf die DB nicht anfassen")
    monkeypatch.setattr(connection, "db", no_db)
    _open_gate()
    ctx = ModuleContext("tasks")
    start = time.perf_counter()
    for i in range(1000):
        ctx.catalog_changed("task", "till", f"t-{i}")
    assert time.perf_counter() - start < 1.0
    assert catalog_changes.pending_count() == 1000


def test_vormerkliste_begrenzt(monkeypatch):
    monkeypatch.setattr(catalog_changes, "MAX_PENDING", 3)
    _open_gate()
    ctx = ModuleContext("tasks")
    for i in range(5):
        ctx.catalog_changed("task", "till", f"t-{i}")
    items, overflow = catalog_changes.drain()
    assert len(items) == 3
    assert overflow is True
    assert not catalog_changes.is_dirty()


def test_mark_changed_prueft_schalter_unter_sperre(monkeypatch):
    """Wettlauf: Schalter wird zwischen erster Prüfung und Sperre abgeschaltet."""
    _open_gate()

    class _SwitchingLock:
        def __enter__(self):
            catalog_changes._gate = catalog_changes._Gate()  # refresh_gate schaltet ab
            return self

        def __exit__(self, *exc):
            return False
    monkeypatch.setattr(catalog_changes, "_lock", _SwitchingLock())
    catalog_changes.mark_changed("task", "till", "t-1")
    assert len(catalog_changes._pending) == 0


def test_refresh_gate_db_fehler_schaltet_ab(monkeypatch):
    from hydrahive.db import federation_catalog as catalog_db

    _open_gate()
    ModuleContext("tasks").catalog_changed("task", "till", "t-1")

    def broken():
        raise RuntimeError("DB weg")
    monkeypatch.setattr(catalog_db, "gate_inputs", broken)
    assert catalog_changes.refresh_gate() is False
    assert catalog_changes.pending_count() == 0
    ModuleContext("tasks").catalog_changed("task", "till", "t-2")
    assert catalog_changes.pending_count() == 0
