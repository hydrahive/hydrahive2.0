"""Ollama: echtes Kontextfenster + Tool-Fähigkeit aus /api/show statt None.

Hintergrund (Bug den till gefunden hat):
- Ollamas OpenAI-`/v1/models` liefert KEIN context_length und KEINE
  Tool-Capability. Der erste Ollama-Merge hat deshalb jedes Modell mit
  context_window=None und tool_use=None in den Catalog geschrieben.
- Folge 1: HydraHive kannte das reale Fenster nicht -> Compaction-Rechnung
  daneben -> Dauer-Compact.
- Folge 2: Ollama selbst deckelt lokal per Default auf num_ctx~4096 (siehe
  "4.096" in tills Screenshots), egal was das Modell theoretisch kann. Wenn
  HydraHive num_ctx nicht mitschickt, wird jeder groessere Prompt abgeschnitten.

Fix-Vertrag (hier als RED-Tests festgenagelt):
1. _fetch_ollama_models fragt pro Modell /api/show ab und traegt das echte
   context_length + tool_use (capabilities enthaelt "tools") ein.
2. num_ctx_for_ollama() leitet aus dem Katalog ein sinnvolles, gedeckeltes
   num_ctx ab, das an LiteLLM/Ollama durchgereicht wird.
3. litellm_call reicht num_ctx an litellm.acompletion durch (nur fuer Ollama).

Alle Importe lazy in der Funktion (Test-Isolation: settings-Singleton nicht
zur Collection-Zeit auf /var/lib/hydrahive2 festnageln).
"""
from __future__ import annotations

import asyncio

import pytest


@pytest.fixture(autouse=True)
def _clear_catalog_cache():
    from hydrahive.llm import catalog
    catalog._cache_clear()
    yield
    catalog._cache_clear()


# --- Fake Ollama-Server (httpx) ---------------------------------------------

class _FakeResp:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeClient:
    """Simuliert /v1/models (GET) und /api/show (POST) eines Ollama-Servers."""

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, headers=None):
        # OpenAI-kompatible Modell-Liste: nur ids, KEIN context_length.
        return _FakeResp({"data": [
            {"id": "qwen3:14b"},
            {"id": "gemma4:latest"},
        ]})

    async def post(self, url, json=None, headers=None):
        model = (json or {}).get("model", "")
        if model.startswith("qwen3"):
            return _FakeResp({
                "model_info": {"qwen3.context_length": 40960},
                "capabilities": ["completion", "tools"],
            })
        # gemma4: grosses Fenster, aber KEINE Tools
        return _FakeResp({
            "model_info": {"gemma3.context_length": 131072},
            "capabilities": ["completion", "vision"],
        })


# --- 1. Catalog holt echtes context_window + tool_use aus /api/show ----------

def test_ollama_catalog_uses_real_context_and_tools(monkeypatch):
    from hydrahive.llm import catalog
    monkeypatch.setattr(catalog.httpx, "AsyncClient", _FakeClient)

    provider = {"id": "ollama", "api_base": "http://localhost:11434", "api_key": ""}
    entries = asyncio.run(catalog._fetch_ollama_models(provider))
    by_id = {e["id"]: e for e in entries}

    qwen = by_id["ollama/qwen3:14b"]
    gemma = by_id["ollama/gemma4:latest"]

    # echtes Fenster aus /api/show, NICHT None
    assert qwen["context_window"] == 40960
    assert gemma["context_window"] == 131072
    # Tool-Faehigkeit aus capabilities
    assert qwen["tool_use"] is True
    assert gemma["tool_use"] is False


# --- 2. num_ctx_for_ollama: sinnvoll + gedeckelt ----------------------------

def test_num_ctx_derived_and_capped():
    from hydrahive.llm._config import num_ctx_for_ollama
    # Modell mit riesigem Fenster wird auf ein VRAM-vertraegliches Cap begrenzt
    assert num_ctx_for_ollama(131072) <= 32768
    # kleines Fenster bleibt unveraendert (nicht kuenstlich aufblasen)
    assert num_ctx_for_ollama(8192) == 8192
    # None/0 -> konservativer, aber brauchbarer Default (kein 2048/4096-Deckel)
    assert num_ctx_for_ollama(None) >= 8192


# --- 3. litellm_call reicht num_ctx an Ollama durch --------------------------

def test_litellm_call_passes_num_ctx_for_ollama(monkeypatch):
    from hydrahive.runner import _llm_bridge_backends as backends

    captured: dict = {}

    class _Msg:
        content = "hi"
        tool_calls = None

    class _Choice:
        message = _Msg()
        finish_reason = "stop"

    class _Resp:
        choices = [_Choice()]
        usage = None

    async def _fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _Resp()

    import litellm
    monkeypatch.setattr(litellm, "acompletion", _fake_acompletion)

    asyncio.run(backends.litellm_call(
        model="ollama/qwen3:14b", system_prompt="s", messages=[],
        tools=[], temperature=0.0, max_tokens=100,
        api_base="http://localhost:11434", num_ctx=16384,
    ))
    # num_ctx muss in den Ollama-spezifischen kwargs landen
    assert captured.get("num_ctx") == 16384 or \
        (captured.get("extra_body") or {}).get("options", {}).get("num_ctx") == 16384


def test_litellm_call_no_num_ctx_for_cloud(monkeypatch):
    """Regression: Cloud-Provider bekommen KEIN num_ctx untergejubelt."""
    from hydrahive.runner import _llm_bridge_backends as backends

    captured: dict = {}

    class _Msg:
        content = "hi"
        tool_calls = None

    class _Choice:
        message = _Msg()
        finish_reason = "stop"

    class _Resp:
        choices = [_Choice()]
        usage = None

    async def _fake_acompletion(**kwargs):
        captured.update(kwargs)
        return _Resp()

    import litellm
    monkeypatch.setattr(litellm, "acompletion", _fake_acompletion)

    asyncio.run(backends.litellm_call(
        model="gpt-4o", system_prompt="s", messages=[],
        tools=[], temperature=0.0, max_tokens=100,
    ))
    assert "num_ctx" not in captured
    assert "extra_body" not in captured
