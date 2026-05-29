"""Forschungs-API-Registry — Model/Seed/Store/Injektion (ohne Netz, ohne PG)."""
from __future__ import annotations

from hydrahive.research._seed import SEED
from hydrahive.research.models import AUTH_TYPES, CATEGORIES


def test_seed_integrity():
    ids = [a.id for a in SEED]
    assert len(ids) == len(set(ids))                      # eindeutige ids
    assert len(SEED) >= 12
    for a in SEED:
        assert a.id and a.base_url and a.name
        assert a.category in CATEGORIES
        assert a.auth_type in AUTH_TYPES
        assert a.url_pattern.startswith("https://")
        if a.needs_key:
            assert a.auth_param or a.auth_type == "bearer"  # wohin der Key geht
        else:
            assert a.enabled                                # keyless ist default aktiv


def test_keyless_pubmed_and_openalex_present():
    by_id = {a.id: a for a in SEED}
    assert by_id["pubmed"].base_url.startswith("https://eutils.ncbi.nlm.nih.gov")
    assert by_id["openalex"].polite_email_param == "mailto"
    assert by_id["core"].needs_key and not by_id["core"].enabled  # Key-Quelle startet aus


# --- Store (verschlüsselt, seed-merge) ---------------------------------------

def test_store_roundtrip_and_seed_merge(tmp_path, monkeypatch):
    import hydrahive.research.store as st
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "research_apis_config", tmp_path / "research_apis.json", raising=False)
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data", raising=False)

    apis = {a.id: a for a in st.list_apis()}
    assert apis["pubmed"].enabled is True
    assert apis["core"].enabled is False                 # Key-Quelle startet aus

    st.set_key("core", "SECRET123")
    st.set_enabled("core", True)
    raw = (tmp_path / "research_apis.json").read_text()
    assert "SECRET123" not in raw                         # Key NICHT im Klartext
    reloaded = st.get_api("core")
    assert reloaded.key == "SECRET123" and reloaded.enabled is True
    assert st.get_api("pubmed").enabled is True           # andere unberührt (seed-merge)


def test_public_list_masks_key(tmp_path, monkeypatch):
    import hydrahive.research.store as st
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "research_apis_config", tmp_path / "r.json", raising=False)
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data", raising=False)
    st.set_key("core", "X")
    pub = {a["id"]: a for a in st.list_public()}
    assert pub["core"]["has_key"] is True and "key" not in pub["core"]


# --- fetch_url-Injektion (match_research_api) --------------------------------

def test_match_injects_bearer_and_query(tmp_path, monkeypatch):
    import hydrahive.research.store as st
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "research_apis_config", tmp_path / "r.json", raising=False)
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data", raising=False)

    st.set_key("core", "K"); st.set_enabled("core", True)            # bearer, needs_key
    bearer = st.match_research_api("https://api.core.ac.uk/v3/search/works?q=x")
    assert bearer is not None and bearer.type == "bearer" and bearer.value == "K"

    st.set_key("openfda", "QK")                                      # query, optionaler Key
    q = st.match_research_api("https://api.fda.gov/drug/event.json?search=x")
    assert q.type == "query" and q.query_param == "api_key" and q.value == "QK"


def test_match_none_for_keyless_or_disabled(tmp_path, monkeypatch):
    import hydrahive.research.store as st
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "research_apis_config", tmp_path / "r.json", raising=False)
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data", raising=False)
    assert st.match_research_api("https://api.openalex.org/works") is None   # keyless
    assert st.match_research_api("https://api.core.ac.uk/v3/x") is None       # disabled, kein Key


# --- Admin-Route (Handler direkt; require_admin selbst in test_auth.py) -------

def test_route_list_masks_and_update(tmp_path, monkeypatch):
    import asyncio

    import pytest
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "research_apis_config", tmp_path / "r.json", raising=False)
    monkeypatch.setattr(settings, "data_dir", tmp_path / "data", raising=False)
    from hydrahive.api.routes import research_apis as rt

    admin = ("test", "admin")
    out = asyncio.run(rt.list_apis(_=admin))
    assert "pubmed" in {a["id"] for a in out["apis"]}
    assert all("key" not in a for a in out["apis"])             # Klartext-Key maskiert

    res = asyncio.run(rt.update_api("core", rt.ApiUpdate(key="Z", enabled=True), _=admin))
    assert res["has_key"] is True and res["enabled"] is True

    with pytest.raises(Exception):                              # 404
        asyncio.run(rt.update_api("nope", rt.ApiUpdate(enabled=True), _=admin))


def test_route_registered():
    from hydrahive.api.routes.research_apis import router
    paths = {r.path for r in router.routes}
    assert "/api/research-apis" in paths
    assert "/api/research-apis/{rid}" in paths
