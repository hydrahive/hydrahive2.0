"""Katalog Etappe 3, Aufgabe 3: Index, Hybrid-Suche und Store (Spec S7, K2, K3, K9; docs/plans/2026-11-26-tool-skill-katalog.md).

Der Katalog ist eine Suchhilfe: Er filtert VOR dem Rang auf die Freigabe des Laufs (kein Leck von Beschreibung oder Schema
gesperrter Tools), enthält nie MCP-Tools und läuft ohne Postgres und ohne Embedding-Modell (nur Wortsuche).
"""
from __future__ import annotations

import asyncio
import hashlib
import math
import re

import pytest

# Zehn Alltagsanfragen → erwartetes Kern-Tool (nur Kern-Tools, damit der Test ohne Module und Plugins läuft).
ANFRAGEN = [
    ("Bild erzeugen", "generate_image"),
    ("Webseite abrufen", "fetch_url"),
    ("im Internet suchen", "web_search"),
    ("Mail schicken", "send_mail"),
    ("Notiz merken", "write_memory"),
    ("Befehl in der Shell ausführen", "shell_exec"),
    ("Text vorlesen lassen", "generate_speech"),
    ("Audio in Text umwandeln", "transcribe_audio"),
    ("PDF lesen", "read_document"),
    ("Musik erzeugen", "generate_music"),
]


def _fake_vec(text: str, dim: int = 256) -> list[float]:
    """Deterministischer Bag-of-words-Vektor (kein Netz): gehashte Wortstämme, normiert."""
    vec = [0.0] * dim
    for tok in re.findall(r"[a-zäöüß0-9]+", text.lower()):
        h = int(hashlib.md5(tok[:5].encode()).hexdigest(), 16) % dim
        vec[h] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


@pytest.fixture
def store():
    from hydrahive.catalog import _store
    _store.reset_store()
    yield _store.get_store()
    _store.reset_store()


@pytest.fixture
def core_names(store):
    from hydrahive.catalog.index import rebuild_tool_index
    from hydrahive.tools import REGISTRY
    assert rebuild_tool_index() > 0
    return {n for n in REGISTRY if n not in ("run_tool", "find_tools", "find_skills")}


def _mit_embedding(store) -> None:
    for e in store.entries():
        store.set_vector(e.name, _fake_vec(f"{e.name} {e.title} {e.text}"))


@pytest.mark.parametrize("embedding", [False, True], ids=["wortsuche", "mit_embedding"])
def test_zehn_alltagsanfragen_top3(store, core_names, embedding):
    from hydrahive.catalog.search import search
    if embedding:
        _mit_embedding(store)
    treffer = 0
    fehlend = []
    for anfrage, erwartet in ANFRAGEN:
        res = search(anfrage, allowed=core_names, kind="tool", limit=3,
                     query_vector=_fake_vec(anfrage) if embedding else None)
        if erwartet in [e.name for e in res]:
            treffer += 1
        else:
            fehlend.append((anfrage, erwartet, [e.name for e in res]))
    assert treffer >= 9, f"{treffer}/10 in den ersten 3: {fehlend}"


def test_gesperrtes_tool_nie_im_ergebnis_auch_nicht_beschreibung(store, core_names):
    from hydrahive.catalog.search import search
    frei = core_names - {"send_mail", "read_mail"}
    res = search("Mail schicken", allowed=frei, kind="tool", limit=10)
    assert "send_mail" not in [e.name for e in res]
    blob = " ".join(f"{e.name} {e.title} {e.text}" for e in res)
    assert "Sendet eine E-Mail" not in blob and "send_mail" not in blob
    assert search("Mail schicken", allowed=set(), kind="tool") == []        # leere Freigabe → nichts


def test_filter_vor_dem_rang_nicht_danach(store, core_names):
    """Mit Limit 1 und gesperrtem Spitzenreiter kommt der nächste FREIGEGEBENE, nicht eine leere Liste."""
    from hydrahive.catalog.search import search
    frei = core_names - {"send_mail"}
    res = search("Mail schicken", allowed=frei, kind="tool", limit=1)
    assert len(res) == 1 and res[0].name != "send_mail"


def test_mcp_nie_im_katalog(store, monkeypatch):
    from hydrahive.catalog.index import rebuild_tool_index
    from hydrahive.tools import REGISTRY
    from hydrahive.tools.base import Tool, ToolResult

    async def _x(args, ctx):
        return ToolResult.ok("x")
    monkeypatch.setitem(REGISTRY, "mcp__srv__werkzeug", Tool(
        name="mcp__srv__werkzeug", description="Ein MCP-Werkzeug", schema={"type": "object", "properties": {}},
        execute=_x))
    rebuild_tool_index()
    assert not [e for e in store.entries() if e.name.startswith("mcp__")]


def test_entferntes_tool_verschwindet(store, monkeypatch):
    """Review-Fokus 4: Ein deinstalliertes Tool wird nicht mehr angeboten."""
    from hydrahive.catalog.index import rebuild_tool_index
    from hydrahive.catalog.search import search
    from hydrahive.tools import REGISTRY
    from hydrahive.tools.base import Tool, ToolResult

    async def _x(args, ctx):
        return ToolResult.ok("x")
    monkeypatch.setitem(REGISTRY, "zebrafinken_zaehler", Tool(
        name="zebrafinken_zaehler", description="Zählt Zebrafinken im Gehege", schema={"type": "object", "properties": {}},
        execute=_x))
    rebuild_tool_index()
    assert [e.name for e in search("Zebrafinken zählen", allowed={"zebrafinken_zaehler"}, kind="tool")] == ["zebrafinken_zaehler"]
    monkeypatch.delitem(REGISTRY, "zebrafinken_zaehler")
    rebuild_tool_index()
    assert search("Zebrafinken zählen", allowed={"zebrafinken_zaehler"}, kind="tool") == []
    assert "zebrafinken_zaehler" not in {e.name for e in store.entries()}


def test_ohne_postgres_wortsuche(store, core_names, monkeypatch):
    """K9: Ohne Pool und ohne Embedding-Modell bleibt es bei der Wortsuche, ohne Fehler."""
    from hydrahive.catalog._store import sync_embeddings
    from hydrahive.catalog.search import search
    assert asyncio.run(sync_embeddings(store, pool=None, model="")) == 0
    assert asyncio.run(sync_embeddings(store, pool=None, model="irgendein/modell")) == 0
    res = search("Bild erzeugen", allowed=core_names, kind="tool", limit=3)
    assert "generate_image" in [e.name for e in res]


def test_postgres_fehler_blockiert_nie(store, core_names):
    """Ein kaputter Pool darf die Suche weder verzögern noch kippen."""
    from hydrahive.catalog._store import sync_embeddings

    class KaputterPool:
        def acquire(self):
            raise RuntimeError("Pool kaputt")
    assert asyncio.run(sync_embeddings(store, pool=KaputterPool(), model="m")) == 0


def test_einträge_haben_vollen_namen_und_art(store, core_names):
    from hydrahive.catalog.index import CatalogEntry
    es = store.entries()
    assert es and all(isinstance(e, CatalogEntry) for e in es)
    assert all(e.kind == "tool" and e.name and e.text for e in es)
    assert {"generate_image", "send_mail"} <= {e.name for e in es}


def test_such_werkzeuge_stehen_nicht_im_katalog(store, core_names):
    names = {e.name for e in store.entries()}
    assert not names & {"run_tool", "find_tools", "find_skills"}


def test_plugin_tools_mit_praefix(store, monkeypatch):
    """S7: Plugin-Tools stehen mit vollem Namen inkl. Präfix im Katalog (eindeutiger Schlüssel)."""
    from hydrahive.catalog import index
    monkeypatch.setattr(index, "_plugin_tools", lambda: [
        {"name": "plugin__git-stats__git_commits", "description": "Zeigt die letzten Git-Commits", "schema": {}}])
    index.rebuild_tool_index()
    assert "plugin__git-stats__git_commits" in {e.name for e in store.entries()}


def test_stabile_reihenfolge_bei_gleichem_rang(store, core_names):
    from hydrahive.catalog.search import search
    a = [e.name for e in search("Datei", allowed=core_names, kind="tool", limit=5)]
    b = [e.name for e in search("Datei", allowed=core_names, kind="tool", limit=5)]
    assert a == b



def test_warm_catalog_baut_index_und_holt_vektoren(monkeypatch):
    """Fängt: sync_embeddings wurde nirgends aufgerufen – im Betrieb gab es nie Vektoren, nur Wortsuche."""
    import asyncio
    from hydrahive.catalog import _store, index
    _store.reset_store()

    class _Pool:
        def acquire(self):
            class _C:
                async def __aenter__(self_inner): return self_inner
                async def __aexit__(self_inner, *a): return False
            return _C()

    async def fake_batch(texts, model, **kw):
        return [[1.0, 0.0, 0.5] for _ in texts]
    monkeypatch.setattr("hydrahive.llm.embed.aembed_batch", fake_batch)
    monkeypatch.setattr("hydrahive.llm._config.load_config", lambda: {"embed_model": "fake"})
    monkeypatch.setattr("hydrahive.db.mirror._pool", _Pool(), raising=False)
    asyncio.run(index.warm_catalog())
    st = _store.get_store()
    assert st.entries() and len(st.vectors()) == len(st.entries())


def test_warm_catalog_ohne_modell_kein_fehler(monkeypatch):
    import asyncio
    from hydrahive.catalog import _store, index
    _store.reset_store()
    monkeypatch.setattr("hydrahive.llm._config.load_config", lambda: {"embed_model": ""})
    asyncio.run(index.warm_catalog())
    assert _store.get_store().entries() and _store.get_store().vectors() == {}


def test_lifespan_startet_warm_catalog():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src/hydrahive/api/lifespan.py").read_text()
    assert "warm_catalog()" in src



# --- Review #783 ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("anfrage,erwartet", [
    ("im Internet suchen", "web_search"), ("Text vorlesen lassen", "generate_speech"),
    ("merk dir das", "write_memory"), ("Webseite aufrufen", "fetch_url"), ("Sprachnachricht abtippen", "transcribe_audio"),
    ("schau im Netz nach", "web_search"),
])
def test_wortsuche_versteht_alltagssynonyme(store, core_names, anfrage, erwartet):
    """Fängt (Review #783, muss): ohne Synonyme fand die Wortsuche diese Alltagsformulierungen nicht (7/10)."""
    from hydrahive.catalog.search import search
    assert erwartet in [e.name for e in search(anfrage, allowed=core_names, kind="tool", limit=3)]


def test_veralteter_vektor_wird_nicht_gespeichert(store):
    """Fängt (Review #783, sollte): Eintrag während des Embeddings ersetzt → alter Vektor blieb stehen."""
    from hydrahive.catalog.index import CatalogEntry
    alt = CatalogEntry(name="x", kind="tool", title="alt", text="alt", category="c", owner_scope="", schema={})
    neu = CatalogEntry(name="x", kind="tool", title="neu", text="neu", category="c", owner_scope="", schema={})
    store.replace_all([alt], kind="tool")
    store.replace_all([neu], kind="tool")                      # während das Embedding für „alt“ lief
    store.set_vector("x", [1.0], for_entry=alt)
    assert store.vectors() == {} and [e.name for e in store.missing_vectors()] == ["x"]
    store.set_vector("x", [1.0], for_entry=neu)
    assert store.vectors() == {"x": [1.0]}


def test_vektoren_ohne_postgres_pool(store, monkeypatch):
    """Fängt (Review #783, sollte): sync_embeddings verlangte einen Pool, obwohl die Vektoren im Speicher liegen."""
    from hydrahive.catalog import _store
    from hydrahive.catalog.index import rebuild_tool_index
    rebuild_tool_index()

    async def fake_batch(texts, model, **kw):
        return [[1.0, 0.0] for _ in texts]
    monkeypatch.setattr("hydrahive.llm.embed.aembed_batch", fake_batch)
    n = asyncio.run(_store.sync_embeddings(store, pool=None, model="fake"))
    assert n == len(store.entries()) > 0


def test_wortsuche_bleibt_schnell_bei_vielen_tools(store):
    """Fängt (Review #783, sollte): df wurde je Eintrag × Begriff neu berechnet (quadratisch)."""
    import time
    from hydrahive.catalog.index import CatalogEntry
    from hydrahive.catalog.search import search
    viele = [CatalogEntry(name=f"t{i}", kind="tool", title=f"Werkzeug {i} für Dateien und Web", text=f"liest schreibt sucht {i}",
                          category="c", owner_scope="", schema={}) for i in range(500)]
    store.replace_all(viele, kind="tool")
    t = time.perf_counter()
    search("Dateien im Web suchen und schreiben", allowed={e.name for e in viele}, kind="tool", limit=5)
    assert time.perf_counter() - t < 0.5
