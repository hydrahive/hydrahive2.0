"""Agenten-Templates: Speicher, Validierung, Start-Templates (Plan E2 T1+T2).

Spec docs/specs/agent-templates.md Kap. 6.
"""
from __future__ import annotations

import threading

import pytest

from hydrahive.agents import templates as tpl
from hydrahive.agents.templates import _store


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(_store, "_path", lambda: tmp_path / "agent_templates.json")
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: {
        "claude-opus-5-5", "claude-sonnet-5", "claude-fable-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"})
    _store.reset_cache()
    yield
    _store.reset_cache()


def base(**over) -> dict:
    t = {"label": "Test", "group": "specialists",
         "chain": ["claude-sonnet-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"],
         "budget": {"max_iterations": 40, "max_tokens": 16384, "timeout_seconds": 600}}
    t.update(over)
    return t


# --- Start-Templates -------------------------------------------------------------------------------------------------

def test_start_templates_beim_ersten_laden():
    ids = {t["id"] for t in tpl.list_templates()}
    assert {"buddy", "assistant", "projekt-master", "reviewer", "security", "backend", "frontend", "recherche",
            "klein", "modul-schreiber", "modul-schnell", "zahnfee", "kompaktierung", "lehren", "hilfe"} <= ids
    assert len(ids) == 15


def test_start_kette_failover_anderer_anbieter_notfall_minimax():
    pm = tpl.get("projekt-master")
    assert pm["chain"] == ["claude-opus-5-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"]
    sec = tpl.get("security")
    assert sec["chain"][0] == "claude-fable-5" and sec["chain"][1].startswith("openai-codex/")
    assert sec.get("on_demand") is True


def test_start_modell_fehlt_im_katalog_stufe_leer(monkeypatch):
    monkeypatch.setattr(tpl._defaults, "_catalog_ids", lambda: {"claude-sonnet-5"})
    _store.reset_cache()
    b = tpl.get("buddy")
    assert b["chain"] == ["claude-sonnet-5"]


def test_wiederholtes_laden_legt_nichts_doppelt_an():
    n = len(tpl.list_templates())
    _store.reset_cache()
    assert len(tpl.list_templates()) == n


# --- Speichern / Versionen -------------------------------------------------------------------------------------------

def test_anlegen_und_aendern_erhoeht_revision():
    a = tpl.save("test-a", base(), by="admin")
    assert a["revision"] == 1 and a["updated_by"] == "admin"
    b = tpl.save("test-a", base(label="Neu"), by="admin")
    assert b["revision"] == 2 and tpl.get("test-a")["label"] == "Neu"
    hist = tpl.history("test-a")
    assert [h["revision"] for h in hist] == [1] and hist[0]["label"] == "Test"


def test_revert_holt_alte_fassung_als_neue_revision():
    tpl.save("test-b", base(label="Eins"), by="admin")
    tpl.save("test-b", base(label="Zwei"), by="admin")
    r = tpl.revert("test-b", 1, by="admin")
    assert r["label"] == "Eins" and r["revision"] == 3


def test_revert_unbekannte_revision():
    tpl.save("test-c", base(), by="admin")
    with pytest.raises(tpl.TemplateError, match="revision_unknown"):
        tpl.revert("test-c", 9, by="admin")


def test_loeschen():
    tpl.save("test-d", base(), by="admin")
    tpl.delete("test-d")
    assert tpl.get("test-d") is None


def test_gleichzeitiges_schreiben_verliert_nichts():
    def write(i):
        tpl.save(f"par-{i}", base(), by="admin")
    threads = [threading.Thread(target=write, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    _store.reset_cache()
    assert {f"par-{i}" for i in range(12)} <= {t["id"] for t in tpl.list_templates()}


# --- Validierung -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("tid", ["A", "1abc", "x", "mit leer", "a" * 42, "ä-x"])
def test_ungueltige_id(tid):
    with pytest.raises(tpl.TemplateError, match="template_id_invalid"):
        tpl.save(tid, base(), by="admin")


@pytest.mark.parametrize(("chain", "code"), [
    ([], "chain_empty"),
    (["a", "b", "c", "d"], "chain_too_long"),
    (["a", "a"], "chain_duplicate"),
    (["a", ""], "chain_entry_empty"),
])
def test_kette(chain, code):
    with pytest.raises(tpl.TemplateError, match=code):
        tpl.save("test-k", base(chain=chain), by="admin")


@pytest.mark.parametrize(("field", "value"), [
    ("max_iterations", 0), ("max_iterations", 251), ("max_tokens", 0), ("max_tokens", 200_001),
    ("timeout_seconds", 29), ("timeout_seconds", 3601), ("overrun_pct", -1), ("overrun_pct", 101),
    ("compact_threshold_pct", 29), ("compact_threshold_pct", 101), ("cooldown_seconds", -1),
])
def test_budget_grenzen(field, value):
    t = base()
    t["budget"][field] = value
    with pytest.raises(tpl.TemplateError, match="budget_out_of_range"):
        tpl.save("test-g", t, by="admin")


def test_budget_unbekannte_werte_reasoning_und_cache():
    t = base()
    t["budget"]["reasoning_effort"] = "maximal"
    with pytest.raises(tpl.TemplateError, match="reasoning_effort_invalid"):
        tpl.save("test-r", t, by="admin")
    t = base()
    t["budget"]["cache_ttl"] = "1d"
    with pytest.raises(tpl.TemplateError, match="cache_ttl_invalid"):
        tpl.save("test-r", t, by="admin")


def test_unbekannte_gruppe():
    with pytest.raises(tpl.TemplateError, match="group_invalid"):
        tpl.save("test-u", base(group="zirkus"), by="admin")


def test_fehlende_budgetwerte_bekommen_standard():
    t = tpl.save("test-s", base(budget={}), by="admin")
    assert t["budget"]["max_iterations"] >= 1 and t["budget"]["overrun_pct"] == 20
    assert t["reply"]["summary_max_chars"] > 0
