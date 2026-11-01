"""MiniMax M3.1-Flash / M3 (Spec docs/specs/minimax-m3.md): Katalog, Denk-Stufen, Bilder, Preise.

Die Live-Antwort ist die echte von api.minimax.io/v1/models (01.11.2026, Key des Admins)."""
from __future__ import annotations

import pytest

from hydrahive.llm import _catalog_data as cd
from hydrahive.llm import catalog
from hydrahive.llm._anthropic import apply_effort, convert_images_for_minimax
from hydrahive.llm._pricing import cost_micros, lookup, provider_from_model
from hydrahive.llm.reasoning_effort import effort_levels_for_model

LIVE = {"object": "list", "data": [
    {"id": i, "object": "model", "created": 1789556118, "owned_by": "minimax"}
    for i in ("MiniMax-M3.1-Flash", "MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5",
              "MiniMax-M2.5-highspeed", "MiniMax-M2.1", "MiniMax-M2.1-highspeed", "MiniMax-M2")]}
FLASH, M3, M27 = "MiniMax-M3.1-Flash", "MiniMax-M3", "MiniMax-M2.7"


@pytest.fixture(autouse=True)
def _clear_cache():
    catalog._cache_clear()
    yield
    catalog._cache_clear()


# ---------- Katalog ----------

def test_minimax_hat_live_endpoint():
    ep = cd.PROVIDER_ENDPOINTS["minimax"]
    assert ep["url"] == "https://api.minimax.io/v1/models" and ep["auth"] == "bearer"


def test_live_antwort_ohne_abgeschaltete_modelle():
    ids = [e["id"] for e in catalog._parse_models_response("minimax", LIVE)]
    assert ids == ["MiniMax-M3.1-Flash", "MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5",
                   "MiniMax-M2.5-highspeed"]


def test_abgeschaltete_nur_fuer_minimax_gefiltert():
    ids = [e["id"] for e in catalog._parse_models_response("openrouter", {"data": [{"id": "MiniMax-M2"}, {"id": "x"}]})]
    assert "openrouter/MiniMax-M2" in ids


def test_fallback_liste_nur_antwortende_modelle():
    assert cd.STATIC_MODELS["minimax"] == ["MiniMax-M3.1-Flash", "MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed",
                                           "MiniMax-M2.5", "MiniMax-M2.5-highspeed"]
    for dead in ("MiniMax-M2.1", "MiniMax-M2", "MiniMax-Text-01", "MiniMax-M1", "abab6.5s-chat", "abab5.5-chat"):
        assert dead not in cd.STATIC_MODELS["minimax"]
        assert dead in cd.RETIRED_MODELS["minimax"]


@pytest.mark.parametrize("model,ctx,vision", [(FLASH, 1_000_000, True), (M3, 1_000_000, True), (M27, 200_000, False)])
def test_metadaten(model, ctx, vision):
    md = cd.METADATA[model]
    assert md["context_window"] == ctx and md["tool_use"] is True and md["category"] == "chat" and md["family"] == "minimax"
    assert bool(md.get("vision")) is vision


async def test_provider_katalog_filtert_auch_die_nutzerliste(monkeypatch):
    async def fake_fetch(pid, key):
        return catalog._parse_models_response("minimax", LIVE)
    monkeypatch.setattr(catalog, "_cached_fetch", fake_fetch)
    monkeypatch.setattr(catalog, "_catalog_credentials", lambda p: ["k"])
    out = await catalog.catalog_for_providers([{"id": "minimax", "name": "MiniMax", "api_key": "k",
                                                "models": ["MiniMax-M2.1", "MiniMax-M3"]}])
    ids = [m["id"] for m in out[0]["models"]]
    assert "MiniMax-M2.1" not in ids and "MiniMax-M3" in ids and out[0]["live_count"] == 6


async def test_fallback_ohne_netz(monkeypatch):
    async def fake_fetch(pid, key):
        return []
    monkeypatch.setattr(catalog, "_cached_fetch", fake_fetch)
    monkeypatch.setattr(catalog, "_catalog_credentials", lambda p: ["k"])
    out = await catalog.catalog_for_providers([{"id": "minimax", "name": "MiniMax", "api_key": "k", "models": []}])
    assert [m["id"] for m in out[0]["models"]] == cd.STATIC_MODELS["minimax"] and out[0]["live_count"] == 0


# ---------- Denk-Stufen ----------

def kw(**extra):
    return {"max_tokens": 4096, "temperature": 0.7, **extra}


@pytest.mark.parametrize("model", [FLASH, M3])
@pytest.mark.parametrize("effort", ["low", "medium", "high", "xhigh", "max"])
def test_m3_mit_stufe_adaptive_und_effort(model, effort):
    k = kw()
    apply_effort(k, model, effort)
    assert k["thinking"] == {"type": "adaptive"} and k["output_config"] == {"effort": effort}
    assert "temperature" not in k and k["max_tokens"] == 4096


def test_m3_flash_ohne_stufe_sendet_nichts_aber_ohne_temperature():
    k = kw()
    apply_effort(k, FLASH, None)
    assert "thinking" not in k and "output_config" not in k


def test_m3_ohne_stufe_kein_denken():
    k = kw()
    apply_effort(k, M3, "")
    assert "thinking" not in k and "output_config" not in k


@pytest.mark.parametrize("model", [FLASH, M3])
def test_unbekannte_stufe_nicht_senden(model):
    k = kw()
    apply_effort(k, model, "ultra")
    assert "thinking" not in k and "output_config" not in k


@pytest.mark.parametrize("effort", ["none", "off", "disabled", "minimal"])
def test_nie_disabled_oder_none(effort):
    k = kw()
    apply_effort(k, FLASH, effort)
    assert "thinking" not in k and "output_config" not in k


def test_m27_bleibt_legacy():
    k = kw()
    apply_effort(k, M27, "medium")
    assert k["thinking"] == {"type": "enabled", "budget_tokens": 4096} and k["temperature"] == 1.0
    assert "output_config" not in k


def test_praefix_minimax_wird_erkannt():
    k = kw()
    apply_effort(k, "minimax/MiniMax-M3.1-Flash", "high")
    assert k["output_config"] == {"effort": "high"} and "temperature" not in k


def test_stufen_je_modell():
    assert effort_levels_for_model(FLASH) == ("low", "medium", "high", "xhigh", "max")
    assert effort_levels_for_model(M3) == ("low", "medium", "high", "xhigh", "max")
    assert effort_levels_for_model(M27) == ("low", "medium", "high")
    assert effort_levels_for_model("MiniMax-M2.5") == ("low", "medium", "high")
    # mit Anbieter-Vorsatz (so stehen Modelle teils in der Agent-Konfiguration)
    assert effort_levels_for_model("minimax/MiniMax-M3.1-Flash") == ("low", "medium", "high", "xhigh", "max")
    assert effort_levels_for_model("minimax/MiniMax-M2.7") == ("low", "medium", "high")


def test_katalog_meldet_effort_unterstuetzung():
    assert catalog._enrich("minimax", {"id": FLASH})["supports_effort"] is True
    assert catalog._enrich("minimax", {"id": M3})["supports_effort"] is True
    assert catalog._enrich("minimax", {"id": M27})["supports_effort"] is False


# ---------- Bilder ----------

IMG = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAAA"}}


def test_bilder_m3_bleiben_anthropic_bloecke():
    msgs = [{"role": "user", "content": [IMG, {"type": "text", "text": "Was ist das?"}]}]
    assert convert_images_for_minimax(msgs, FLASH) == msgs
    assert convert_images_for_minimax(msgs, M3) == msgs
    assert convert_images_for_minimax(msgs, "minimax/MiniMax-M3") == msgs


def test_bilder_m2_werden_wie_bisher_umgebaut():
    out = convert_images_for_minimax([{"role": "user", "content": [IMG]}], M27)
    assert out[0]["content"][0] == {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}


def test_bilder_ohne_modellangabe_wie_bisher():
    out = convert_images_for_minimax([{"role": "user", "content": [IMG]}])
    assert out[0]["content"][0]["type"] == "image_url"


# ---------- Preise ----------

def test_anbieter_wird_erkannt():
    assert provider_from_model(FLASH) == "minimax" and provider_from_model("minimax/MiniMax-M3") == "minimax"


def test_preise_flash_und_m3():
    f, m = lookup("minimax", FLASH), lookup("minimax", M3)
    assert (f.input, f.output, f.cache_read, f.cache_creation) == (0.015, 0.06, 0.0015, 0.015)
    assert (m.input, m.output, m.cache_read, m.cache_creation) == (0.03, 0.12, 0.006, 0.03)
    assert lookup("minimax", "minimax/MiniMax-M3") == m
    assert lookup("minimax", M27) is None


def test_kosten_flash():
    # 1 Mio. Eingabe + 1 Mio. Ausgabe + 1 Mio. Cache gelesen = 0,15 + 0,60 + 0,015 = 0,765 USD = 76,5 Cent = 76 500 Mikro-Cent
    assert cost_micros("minimax", FLASH, prompt_tokens=1_000_000, completion_tokens=1_000_000,
                       cache_read_tokens=1_000_000, cache_creation_tokens=0) == 76_500


def test_kosten_m3_ohne_cache_und_unbekanntes_modell():
    # 2 Mio. Eingabe (0,60) + 1 Mio. Ausgabe (1,20) = 1,80 USD = 180 Cent = 180 000 Mikro-Cent
    assert cost_micros("minimax", M3, prompt_tokens=2_000_000, completion_tokens=1_000_000,
                       cache_read_tokens=0, cache_creation_tokens=0) == 180_000
    assert cost_micros("minimax", M27, prompt_tokens=10, completion_tokens=10, cache_read_tokens=0,
                       cache_creation_tokens=0) is None
