# Live-Modell-SSOT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provider-Modelle live aus den Provider-Endpoints statt hardcoded — eine Quelle (Live-Fetch + 5-Min-Cache + statischer Fallback), Agent wählt direkt aus der Live-Liste mit Suche + „nur gratis"-Filter.

**Architecture:** `catalog.py` wird zur SSOT: holt live von `/v1/models` (7 Provider inkl. Anthropic), liest pricing/context aus, cached 5 min im Memory. `validate_model` prüft gegen die Live-Liste (winkt bei leerer Liste durch). Frontend: `KNOWN_PROVIDERS`-Modelllisten + `ProviderForm`-Modellauswahl entfallen; Agent-Auswahl + Katalog ziehen live, mit free-Badge/Filter.

**Tech Stack:** Python 3.12 + FastAPI + httpx (Backend), pytest, React + TypeScript (Frontend).

**Design:** `docs/superpowers/specs/2026-05-31-live-models-ssot-design.md`. SPEC-konform (SPEC.md:252-257 fordert „Live aus dem Provider-Endpoint … Suche + Filter" bereits).

**Test-Hinweis:** Backend `cd core && python3 -m pytest tests/test_catalog*.py -q`. Frontend NUR `cd frontend && ./node_modules/.bin/tsc -b` (NIE `--noEmit` — toter Wächter). ruff: `~/.cache/pipx/8b939eaf3702238/bin/ruff`.

---

## File Structure

| Datei | Verantwortung | Aktion |
|---|---|---|
| `core/src/hydrahive/llm/catalog.py` | Live-Fetch → strukturierte Einträge (pricing/free/context), TTL-Cache | Modify |
| `core/src/hydrahive/llm/_catalog_data.py` | Anthropic-Endpoint + Auth-Modus `x-api-key` | Modify |
| `core/src/hydrahive/agents/_validation.py` | `validate_model` gegen Live-Liste, durchwinken bei leer | Modify |
| `core/tests/test_catalog_live.py` | Pricing/free-Parsing, Cache, Anthropic-Auth, Fallback | Create |
| `core/tests/test_validate_model_live.py` | Validierung gegen Live-Liste + Durchwinken | Create |
| `frontend/src/features/llm/api.ts` | `CatalogModel` um `is_free`/pricing erweitern | Modify |
| `frontend/src/features/llm/_llm_providers.ts` | Modell-Arrays raus, nur Provider-Metadaten | Modify |
| `frontend/src/features/llm/ProviderForm.tsx` | Modell-Checkboxen + custom-Feld raus | Modify |
| `frontend/src/features/llm/CatalogPage.tsx` | „nur gratis"-Filter + free-Badge | Modify |
| `frontend/src/features/agents/api.ts` | `getModels` zieht aus `/llm/catalog` (live) | Modify |
| `frontend/src/features/agents/_ModelTab.tsx` | `<select>` → Such-Combobox mit free-Badge | Modify |

---

## PHASE 1 — Backend (SSOT)

### Task 1: catalog.py liefert pricing/free + context aus der Live-Antwort

**Files:**
- Modify: `core/src/hydrahive/llm/catalog.py`
- Test: `core/tests/test_catalog_live.py`

- [ ] **Step 1: Failing test schreiben**

`core/tests/test_catalog_live.py`:
```python
from __future__ import annotations

from hydrahive.llm import catalog


# OpenRouter-/models-Antwortformat (gekürzt): pricing als Strings, context_length.
_OPENROUTER_RESPONSE = {
    "data": [
        {"id": "meta-llama/llama-3.3-70b-instruct:free",
         "context_length": 131072,
         "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "anthropic/claude-sonnet-4-6",
         "context_length": 200000,
         "pricing": {"prompt": "0.000003", "completion": "0.000015"}},
    ]
}


def test_parse_models_marks_free_and_paid():
    entries = catalog._parse_models_response("openrouter", _OPENROUTER_RESPONSE)
    by_id = {e["id"]: e for e in entries}
    free = by_id["openrouter/meta-llama/llama-3.3-70b-instruct:free"]
    paid = by_id["openrouter/anthropic/claude-sonnet-4-6"]
    assert free["is_free"] is True
    assert free["context_window"] == 131072
    assert paid["is_free"] is False
    assert paid["price_prompt"] == "0.000003"


def test_parse_models_without_pricing_is_free_none():
    # OpenAI /models liefert kein pricing-Feld
    entries = catalog._parse_models_response("openai", {"data": [{"id": "gpt-4o"}]})
    assert entries[0]["id"] == "openai/gpt-4o"
    assert entries[0]["is_free"] is None
    assert entries[0]["context_window"] is None
```

- [ ] **Step 2: Test ausführen, Fehlschlag prüfen**

Run: `cd core && python3 -m pytest tests/test_catalog_live.py -q`
Expected: FAIL (`AttributeError: module 'hydrahive.llm.catalog' has no attribute '_parse_models_response'`)

- [ ] **Step 3: `_parse_models_response` implementieren**

In `core/src/hydrahive/llm/catalog.py` eine neue Funktion ergänzen (nach `_normalize_id`):
```python
def _parse_models_response(provider_id: str, data: dict) -> list[dict]:
    """Extrahiert strukturierte Modell-Einträge aus der /v1/models-Antwort.

    OpenRouter liefert pricing (Strings) + context_length; andere Provider oft nur id.
    is_free = pricing.prompt und .completion sind beide '0'. Ohne pricing → None.
    """
    raw: list[dict]
    if isinstance(data.get("data"), list):
        raw = data["data"]
    elif isinstance(data.get("models"), list):  # Gemini
        raw = [{"id": m.get("name", "").replace("models/", "")} for m in data["models"] if m.get("name")]
    else:
        raw = []

    out: list[dict] = []
    for m in raw:
        mid = m.get("id", "")
        if not mid:
            continue
        pricing = m.get("pricing") or {}
        prompt = pricing.get("prompt")
        completion = pricing.get("completion")
        is_free: bool | None
        if prompt is None and completion is None:
            is_free = None
        else:
            is_free = (str(prompt) == "0" and str(completion) == "0")
        out.append({
            "id": _normalize_id(provider_id, mid),
            "context_window": m.get("context_length"),
            "is_free": is_free,
            "price_prompt": prompt,
            "price_completion": completion,
        })
    return out
```

- [ ] **Step 4: Test ausführen, Erfolg prüfen**

Run: `cd core && python3 -m pytest tests/test_catalog_live.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: `_fetch_live_models` + `_enrich` + `catalog_for_providers` auf strukturierte Einträge umstellen**

In `catalog.py` `_fetch_live_models` so ändern, dass es `_parse_models_response` nutzt und `list[dict]` (statt `list[str]`) zurückgibt:
```python
async def _fetch_live_models(provider_id: str, api_key: str) -> list[dict]:
    """Holt strukturierte Modell-Einträge live. Bei Fehler: leere Liste."""
    cfg = PROVIDER_ENDPOINTS.get(provider_id, {})
    url = cfg.get("url")
    if not url or not api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers, params = _auth_for(cfg, api_key)
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
        return _parse_models_response(provider_id, data)
    except Exception as e:
        logger.warning("Catalog: live-fetch für %s fehlgeschlagen: %s", provider_id, e)
        return []
```
Und einen Auth-Helper ergänzen (ersetzt das inline if/else; bereitet Task 2 vor):
```python
def _auth_for(cfg: dict, api_key: str) -> tuple[dict, dict]:
    """Gibt (headers, params) für den Provider-Auth-Modus zurück."""
    kind = cfg.get("auth")
    if kind == "bearer":
        return {"Authorization": f"Bearer {api_key}"}, {}
    if kind == "query":
        return {}, {cfg.get("query_param", "key"): api_key}
    if kind == "x-api-key":  # Anthropic
        return {"x-api-key": api_key, "anthropic-version": "2023-06-01"}, {}
    return {}, {}
```
`_enrich` so anpassen, dass es einen strukturierten Live-Eintrag mit METADATA mergt (Live-Werte haben Vorrang für context_window):
```python
def _enrich(provider_id: str, entry: dict) -> dict[str, Any]:
    """Joint Live-Eintrag mit METADATA. Live-context_window hat Vorrang."""
    md = METADATA.get(entry["id"], {})
    return {
        "id": entry["id"],
        "context_window": entry.get("context_window") or md.get("context_window"),
        "tool_use": md.get("tool_use"),
        "category": md.get("category", "chat"),
        "family": md.get("family", "?"),
        "is_free": entry.get("is_free"),
        "price_prompt": entry.get("price_prompt"),
        "price_completion": entry.get("price_completion"),
        "unknown": entry["id"] not in METADATA,
    }
```
`catalog_for_providers.one` anpassen: live-Einträge holen, bei leer auf `STATIC_MODELS` (als ID-only-Einträge) zurückfallen:
```python
    async def one(p: dict) -> dict:
        pid = p.get("id", "")
        key = p.get("api_key", "") or (p.get("oauth") or {}).get("access", "")
        entries = await _fetch_live_models(pid, key)
        if not entries:
            entries = [{"id": _normalize_id(pid, m), "context_window": None,
                        "is_free": None, "price_prompt": None, "price_completion": None}
                       for m in STATIC_MODELS.get(pid, [])]
        models = [_enrich(pid, e) for e in entries]
        return {
            "provider_id": pid, "provider_name": p.get("name", pid),
            "configured": bool(key), "models": models, "live_count": len(entries),
        }
```

- [ ] **Step 6: Volle catalog-Tests + ruff + commit**

Run: `cd core && python3 -m pytest tests/test_catalog_live.py -q` → PASS
```bash
~/.cache/pipx/8b939eaf3702238/bin/ruff check core/src/hydrahive/llm/catalog.py core/tests/test_catalog_live.py
cd /home/till/claudeneu
git add core/src/hydrahive/llm/catalog.py core/tests/test_catalog_live.py
git commit -m "feat(llm): catalog liest pricing/free + context aus Live-Antwort"
```

---

### Task 2: Anthropic als 7. Live-Provider

**Files:**
- Modify: `core/src/hydrahive/llm/_catalog_data.py:21`
- Test: `core/tests/test_catalog_live.py` (ergänzen)

- [ ] **Step 1: Failing test ergänzen**

In `core/tests/test_catalog_live.py` ergänzen:
```python
def test_anthropic_endpoint_uses_x_api_key():
    from hydrahive.llm._catalog_data import PROVIDER_ENDPOINTS
    ep = PROVIDER_ENDPOINTS["anthropic"]
    assert ep["url"] == "https://api.anthropic.com/v1/models"
    assert ep["auth"] == "x-api-key"


def test_auth_for_x_api_key():
    headers, params = catalog._auth_for({"auth": "x-api-key"}, "sk-ant-xxx")
    assert headers["x-api-key"] == "sk-ant-xxx"
    assert headers["anthropic-version"] == "2023-06-01"
    assert params == {}
```

- [ ] **Step 2: Test ausführen, Fehlschlag prüfen**

Run: `cd core && python3 -m pytest tests/test_catalog_live.py::test_anthropic_endpoint_uses_x_api_key -q`
Expected: FAIL (`ep["url"]` ist `None`)

- [ ] **Step 3: Anthropic-Endpoint setzen**

In `core/src/hydrahive/llm/_catalog_data.py` die Anthropic-Zeile ersetzen:
```python
    "anthropic":    {"url": "https://api.anthropic.com/v1/models", "auth": "x-api-key"},
```
(MiniMax + openai-codex bleiben `{"url": None, "auth": None}`.) Die Anthropic-Antwort hat `{"data": [{"id": "claude-..."}]}` — wird von `_parse_models_response` bereits korrekt geparst (kein pricing → is_free=None).

- [ ] **Step 4: Test ausführen, Erfolg prüfen**

Run: `cd core && python3 -m pytest tests/test_catalog_live.py -q`
Expected: PASS (alle)

- [ ] **Step 5: ruff + commit**

```bash
~/.cache/pipx/8b939eaf3702238/bin/ruff check core/src/hydrahive/llm/_catalog_data.py
cd /home/till/claudeneu
git add core/src/hydrahive/llm/_catalog_data.py core/tests/test_catalog_live.py
git commit -m "feat(llm): Anthropic als Live-Provider (GET /v1/models, x-api-key)"
```

> **Bau-Verifikation (manuell, Till):** Mit echtem Anthropic-Key/OAuth testen, dass `/api/llm/catalog` Anthropic-Modelle live liefert. Bei OAuth-Anthropic muss `_auth_for` ggf. den Bearer-Pfad nehmen — der access-Token liegt schon in `key` (catalog_for_providers nutzt `oauth.access`). Falls Anthropic den OAuth-Token nicht auf /v1/models akzeptiert: STATIC_MODELS["anthropic"] bleibt als Fallback automatisch aktiv.

---

### Task 3: TTL-Cache (5 min) für Live-Fetch

**Files:**
- Modify: `core/src/hydrahive/llm/catalog.py`
- Test: `core/tests/test_catalog_live.py` (ergänzen)

- [ ] **Step 1: Failing test ergänzen**

```python
import asyncio


def test_cache_hit_skips_second_fetch(monkeypatch):
    calls = {"n": 0}

    async def fake_fetch(pid, key):
        calls["n"] += 1
        return [{"id": "openrouter/x", "context_window": None, "is_free": True,
                 "price_prompt": "0", "price_completion": "0"}]

    monkeypatch.setattr(catalog, "_fetch_live_models", fake_fetch)
    catalog._cache_clear()
    providers = [{"id": "openrouter", "api_key": "k"}]
    asyncio.run(catalog.catalog_for_providers(providers))
    asyncio.run(catalog.catalog_for_providers(providers))
    assert calls["n"] == 1  # zweiter Aufruf aus Cache
```

- [ ] **Step 2: Test ausführen, Fehlschlag prüfen**

Run: `cd core && python3 -m pytest tests/test_catalog_live.py::test_cache_hit_skips_second_fetch -q`
Expected: FAIL (`calls["n"] == 2`, kein Cache; bzw. `_cache_clear` fehlt)

- [ ] **Step 3: TTL-Cache implementieren**

In `catalog.py` oben (nach den Imports) ergänzen:
```python
import time

_CACHE_TTL = 300  # 5 Minuten (Hermes-Muster)
_cache: dict[str, tuple[float, list[dict]]] = {}
_cache_locks: dict[str, asyncio.Lock] = {}


def _cache_clear() -> None:
    _cache.clear()


async def _cached_fetch(provider_id: str, api_key: str) -> list[dict]:
    """Live-Fetch mit 5-Min-TTL-Cache + Lock gegen parallele Fetches."""
    now = time.monotonic()
    hit = _cache.get(provider_id)
    if hit and now - hit[0] < _CACHE_TTL:
        return hit[1]
    lock = _cache_locks.setdefault(provider_id, asyncio.Lock())
    async with lock:
        hit = _cache.get(provider_id)  # zweiter Check nach Lock
        if hit and time.monotonic() - hit[0] < _CACHE_TTL:
            return hit[1]
        entries = await _fetch_live_models(provider_id, api_key)
        if entries:  # nur erfolgreiche Fetches cachen
            _cache[provider_id] = (time.monotonic(), entries)
        return entries
```
In `catalog_for_providers.one` den direkten `_fetch_live_models`-Aufruf durch `_cached_fetch` ersetzen:
```python
        entries = await _cached_fetch(pid, key)
```
(`time.monotonic()` statt `time.time()` ist erlaubt — kein Date-Verbot, das gilt nur in Workflow-Scripts.)

- [ ] **Step 4: Test ausführen, Erfolg prüfen**

Run: `cd core && python3 -m pytest tests/test_catalog_live.py -q`
Expected: PASS (alle)

- [ ] **Step 5: ruff + commit**

```bash
~/.cache/pipx/8b939eaf3702238/bin/ruff check core/src/hydrahive/llm/catalog.py
cd /home/till/claudeneu
git add core/src/hydrahive/llm/catalog.py core/tests/test_catalog_live.py
git commit -m "feat(llm): 5-Min-TTL-Cache für Live-Modell-Fetch (Lock gegen Parallel-Fetch)"
```

---

### Task 4: validate_model gegen Live-Liste, durchwinken bei leer

**Files:**
- Modify: `core/src/hydrahive/agents/_validation.py:46-58`
- Test: `core/tests/test_validate_model_live.py`

- [ ] **Step 1: Failing test schreiben**

`core/tests/test_validate_model_live.py`:
```python
from __future__ import annotations

import pytest

from hydrahive.agents import _validation
from hydrahive.agents._validation import AgentValidationError


def test_empty_model_rejected():
    with pytest.raises(AgentValidationError):
        _validation.validate_model("")


def test_passes_through_when_no_available_list(monkeypatch):
    # Keine kuratierte provider.models, kein Live-Katalog erreichbar → durchwinken
    monkeypatch.setattr(_validation, "_available_models", lambda: [])
    _validation.validate_model("openrouter/whatever:free")  # darf NICHT raisen


def test_accepts_model_in_available(monkeypatch):
    monkeypatch.setattr(_validation, "_available_models", lambda: ["openrouter/x", "claude-sonnet-4-6"])
    _validation.validate_model("claude-sonnet-4-6")


def test_rejects_unknown_when_list_present(monkeypatch):
    monkeypatch.setattr(_validation, "_available_models", lambda: ["openrouter/x"])
    with pytest.raises(AgentValidationError):
        _validation.validate_model("totally-made-up")
```

- [ ] **Step 2: Test ausführen, Fehlschlag prüfen**

Run: `cd core && python3 -m pytest tests/test_validate_model_live.py -q`
Expected: FAIL (`_available_models` existiert nicht)

- [ ] **Step 3: validate_model umstellen**

In `core/src/hydrahive/agents/_validation.py` `validate_model` ersetzen und einen Helper einführen:
```python
def _available_models() -> list[str]:
    """Verfügbare Modell-IDs aus dem gecachten Live-Katalog (best effort).

    Leere Liste = keine Info → validate_model winkt durch (kein Bruch bei
    Fetch-Fehler oder Erst-Setup). Nutzt den Catalog-Cache; kein eigener Fetch.
    """
    try:
        from hydrahive.llm.catalog import _cache
    except Exception:
        return []
    out: list[str] = []
    for _ts, entries in _cache.values():
        out.extend(e["id"] for e in entries)
    return out


def validate_model(model: str) -> None:
    """Modell darf nicht leer sein; wenn eine Live-Liste vorliegt, muss das Modell
    drin sein — sonst (leere Liste) durchwinken (Erst-Setup / Fetch-Fehler)."""
    if not model:
        raise AgentValidationError("Modell darf nicht leer sein")
    available = _available_models()
    if available and model not in available:
        raise AgentValidationError(
            f"Modell '{model}' ist nicht in der Live-Modell-Liste verfügbar."
        )
```
(Der alte `llm_client._load_config()`-Zugriff auf `provider.models` entfällt — `provider.models` ist keine Kuratierungsquelle mehr.)

- [ ] **Step 4: Test ausführen, Erfolg prüfen**

Run: `cd core && python3 -m pytest tests/test_validate_model_live.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Regressions-Check + ruff + commit**

Run: `cd core && python3 -m pytest tests/ -q -k "validation or agent" 2>&1 | tail -5` → keine neuen Fehler
```bash
~/.cache/pipx/8b939eaf3702238/bin/ruff check core/src/hydrahive/agents/_validation.py core/tests/test_validate_model_live.py
cd /home/till/claudeneu
git add core/src/hydrahive/agents/_validation.py core/tests/test_validate_model_live.py
git commit -m "feat(agents): validate_model gegen Live-Liste, durchwinken bei leerer Liste"
```

---

## PHASE 2 — Frontend (live ziehen + free-Filter)

### Task 5: CatalogModel-Typ + getModels live; KNOWN_PROVIDERS-Modelle raus

**Files:**
- Modify: `frontend/src/features/llm/api.ts:64-72` (CatalogModel)
- Modify: `frontend/src/features/agents/api.ts:33-42` (getModels)
- Modify: `frontend/src/features/llm/_llm_providers.ts` (Modell-Arrays leeren)

- [ ] **Step 1: CatalogModel um free/pricing erweitern**

In `frontend/src/features/llm/api.ts` das `CatalogModel`-Interface ergänzen:
```typescript
export interface CatalogModel {
  id: string
  context_window: number | null
  tool_use: boolean | null
  category: string
  family: string
  params?: string
  unknown: boolean
  is_free: boolean | null
  price_prompt: string | null
  price_completion: string | null
}
```

- [ ] **Step 2: getModels zieht aus dem Live-Katalog**

In `frontend/src/features/agents/api.ts` `llmInfoApi.getModels` umstellen — statt `flatMap(provider.models)` aus dem Katalog ziehen. Neuer Rückgabetyp behält `models: string[]` (IDs, für bestehende Komponenten) + liefert die strukturierten Einträge mit:
```typescript
import type { CatalogModel } from "@/features/llm/api"

export interface LlmProviderInfo {
  models: string[]              // IDs (Abwärtskompat. für CompactionSection/Fallback)
  catalog: CatalogModel[]       // strukturiert (für ModelTab-Combobox: free-Badge/Filter)
  default_model: string
}

export const llmInfoApi = {
  getModels: async (): Promise<LlmProviderInfo> => {
    const [cfg, cat] = await Promise.all([
      api.get<{ default_model: string }>("/llm"),
      api.get<{ providers: { models: CatalogModel[] }[] }>("/llm/catalog"),
    ])
    const catalog = cat.providers.flatMap((p) => p.models)
    return { models: catalog.map((m) => m.id), catalog, default_model: cfg.default_model }
  },
}
```

- [ ] **Step 3: KNOWN_PROVIDERS-Modell-Arrays leeren**

In `frontend/src/features/llm/_llm_providers.ts` bei JEDEM Provider die `models: [...]`-Liste auf `models: []` setzen (Provider-Metadaten id/name/placeholder/auth bleiben). Beispiel openrouter:
```typescript
  { id: "openrouter", name: "OpenRouter", placeholder: "sk-or-...", models: [] },
```
(Alle 10 Provider analog — die langen Modell-Arrays inkl. NVIDIA-171 verschwinden.)

- [ ] **Step 4: tsc -b grün**

Run: `cd frontend && ./node_modules/.bin/tsc -b`
Expected: Exit 0 (ggf. zeigt es ungenutzte `models`-Referenzen in ProviderForm — die fixt Task 7; falls tsc bricht, Task 7 vorziehen).

- [ ] **Step 5: commit**

```bash
cd /home/till/claudeneu
git add frontend/src/features/llm/api.ts frontend/src/features/agents/api.ts frontend/src/features/llm/_llm_providers.ts
git commit -m "feat(llm): Agent-Modelle live aus Katalog, KNOWN_PROVIDERS-Modelllisten entfernt"
```

---

### Task 6: _ModelTab — Such-Combobox mit free-Badge/Filter

**Files:**
- Modify: `frontend/src/features/agents/_ModelTab.tsx`
- Modify: `frontend/src/features/agents/AgentsPage.tsx` (catalog durchreichen)
- Modify: `frontend/src/features/agents/AgentForm.tsx` (catalog-Prop)

- [ ] **Step 1: AgentsPage lädt + reicht catalog durch**

In `frontend/src/features/agents/AgentsPage.tsx` den State erweitern: aus `getModels()` zusätzlich `catalog` speichern und an `AgentForm` reichen.
```typescript
  const [models, setModels] = useState<string[]>([])
  const [catalog, setCatalog] = useState<import("@/features/llm/api").CatalogModel[]>([])
  // in der getModels-then-Kette:
  llmInfoApi.getModels().then((info) => { setModels(info.models); setCatalog(info.catalog) })
```
`catalog` als Prop an `<AgentForm ... catalog={catalog} />` und in `AgentForm.tsx` an `<ModelTab ... catalog={catalog} />` weiterreichen (Prop-Typ ergänzen).

- [ ] **Step 2: _ModelTab Modell-`<select>` durch Combobox ersetzen**

In `frontend/src/features/agents/_ModelTab.tsx` die Props um `catalog: CatalogModel[]` erweitern und das Modell-`<select>` (Zeile 16-25) durch eine Such-Combobox ersetzen:
```tsx
import { useMemo, useState } from "react"
import type { CatalogModel } from "@/features/llm/api"
// Props: { draft, models, catalog, onChange }

function ModelPicker({ value, catalog, onChange }: {
  value: string; catalog: CatalogModel[]; onChange: (m: string) => void
}) {
  const [q, setQ] = useState("")
  const [onlyFree, setOnlyFree] = useState(false)
  const filtered = useMemo(() => catalog.filter((m) =>
    (!onlyFree || m.is_free === true) &&
    (q === "" || m.id.toLowerCase().includes(q.toLowerCase()))
  ).slice(0, 100), [catalog, q, onlyFree])

  return (
    <div className="space-y-1">
      <div className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Modell suchen…"
          className="flex-1 px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200" />
        <label className="flex items-center gap-1 text-[10px] text-zinc-400 whitespace-nowrap">
          <input type="checkbox" checked={onlyFree} onChange={(e) => setOnlyFree(e.target.checked)} />
          nur gratis
        </label>
      </div>
      <select value={value} onChange={(e) => onChange(e.target.value)} size={6}
        className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono">
        {!catalog.some((m) => m.id === value) && value && <option value={value}>{value} (aktuell)</option>}
        {filtered.map((m) => (
          <option key={m.id} value={m.id}>{m.is_free === true ? "🆓 " : ""}{m.id}</option>
        ))}
      </select>
      {filtered.length === 100 && <p className="text-[10px] text-zinc-600">…verfeinere die Suche (max 100 angezeigt)</p>}
    </div>
  )
}
```
Im `ModelTab`-Body das alte `<select>` durch `<ModelPicker value={draft.llm_model} catalog={catalog} onChange={(m) => onChange({ llm_model: m })} />` ersetzen. `FallbackModelsSelector` nutzt weiter `models: string[]` (unverändert).

- [ ] **Step 3: tsc -b grün**

Run: `cd frontend && ./node_modules/.bin/tsc -b`
Expected: Exit 0

- [ ] **Step 4: commit**

```bash
cd /home/till/claudeneu
git add frontend/src/features/agents/_ModelTab.tsx frontend/src/features/agents/AgentsPage.tsx frontend/src/features/agents/AgentForm.tsx
git commit -m "feat(agents): Modell-Auswahl als Such-Combobox mit free-Filter/Badge"
```

---

### Task 7: ProviderForm vereinfachen (keine Modellauswahl mehr)

**Files:**
- Modify: `frontend/src/features/llm/ProviderForm.tsx`

- [ ] **Step 1: Modell-Checkboxen + custom-Feld entfernen**

In `frontend/src/features/llm/ProviderForm.tsx`:
- Den ganzen `{known && (...)}`-Block (Zeile 92-111: Modell-Checkboxen + custom-Input) entfernen.
- `selectedModels`/`customModel`-State + `toggleModel` entfernen.
- `handleSubmit`: `models` ist jetzt immer `[]` (keine Vorauswahl):
```tsx
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSave({ ...form, name: form.name || known?.name || form.id, models: [] })
    if (!isEdit) setForm({ ...EMPTY_PROVIDER })
  }
```
- Submit-Button-`disabled` (Zeile 114-115): die `selectedModels`/`customModel`-Bedingung streichen, nur `!form.id || (!isOAuth && !form.api_key) || (isOAuth && !hasToken)` behalten.
- Einen Hinweis-Text ergänzen wo der Block war: „Modelle werden live vom Provider geladen und im Agent ausgewählt."

- [ ] **Step 2: tsc -b grün**

Run: `cd frontend && ./node_modules/.bin/tsc -b`
Expected: Exit 0 (keine ungenutzten Imports/Vars mehr)

- [ ] **Step 3: commit**

```bash
cd /home/till/claudeneu
git add frontend/src/features/llm/ProviderForm.tsx
git commit -m "feat(llm): ProviderForm ohne Modell-Vorauswahl (Modelle kommen live)"
```

---

### Task 8: CatalogPage — free-Badge + „nur gratis"-Filter

**Files:**
- Modify: `frontend/src/features/llm/CatalogPage.tsx`

- [ ] **Step 1: Filter-Option + Badge ergänzen**

In `frontend/src/features/llm/CatalogPage.tsx`:
- Den `filter`-State-Typ (Zeile 12) um `"free"` erweitern: `"all" | "tool_use" | "no_tools" | "unknown" | "free"`.
- In der Filter-Logik (wo `filter` angewandt wird) ergänzen: bei `"free"` nur `m.is_free === true`.
- Einen Filter-Button „nur gratis" in der Filter-Leiste hinzufügen (gleicher Stil wie die bestehenden).
- In der Modell-Zeile ein Badge rendern: `{m.is_free === true && <span className="text-[10px] text-emerald-400 ml-1">gratis</span>}`.

- [ ] **Step 2: tsc -b + voller Build grün**

Run: `cd frontend && ./node_modules/.bin/tsc -b && npx vite build 2>&1 | tail -3`
Expected: beide Exit 0

- [ ] **Step 3: commit**

```bash
cd /home/till/claudeneu
git add frontend/src/features/llm/CatalogPage.tsx
git commit -m "feat(llm): Katalog mit free-Badge + 'nur gratis'-Filter"
```

---

### Task 9: Verify (Till, im Browser)

> Nach Update auf dem Server (zieht main):

- [ ] OpenRouter-Provider: in der Agent-Modell-Auswahl erscheinen **alle** Live-Modelle (nicht nur 5), Suche funktioniert
- [ ] „nur gratis"-Filter zeigt die kostenlosen (`:free`), Badge sichtbar
- [ ] Ein kostenloses Modell auswählen + Agent speichern → kein Validierungsfehler, Agent läuft im Chat
- [ ] Anthropic: Modelle erscheinen live (oder via STATIC-Fallback, falls OAuth-Token /v1/models nicht erlaubt — dann sind die statischen da)
- [ ] Bestehender Agent mit altem Modell: Modell bleibt gewählt, kein Bruch
- [ ] Katalog-Seite (Admin): free-Badge + „nur gratis"-Filter funktionieren

---

## Self-Review (vom Plan-Autor durchgeführt)

**Spec-Coverage:** Live-Fetch als SSOT (T1-T3) ✓; Anthropic 7. Provider (T2) ✓; 5-Min-Cache+Lock (T3) ✓; pricing/free (T1) ✓; validate_model durchwinken (T4) ✓; Agent wählt aus Live-Liste (T5-T6) ✓; Suche+free-Filter (T6, T8) ✓; KNOWN_PROVIDERS-Modelle raus (T5) ✓; ProviderForm ohne Vorauswahl (T7) ✓; kein Bruch/Migration (T4 durchwinken + T6 „aktuell"-Option) ✓; Drift-Elimination (T5) ✓.

**Platzhalter-Scan:** Kein TBD/TODO; Code-Steps enthalten vollständigen Code. T7/T8 beschreiben präzise Edits an bekannten Zeilen (Block entfernen / Filter ergänzen) statt vollständigem Datei-Dump — die Stellen sind exakt benannt. Anthropic-OAuth-Auth ist als Bau-Verifikation markiert (ehrlicher offener Punkt, mit Fallback).

**Typ-Konsistenz:** `_parse_models_response`/`_fetch_live_models`/`_cached_fetch`/`_enrich` geben durchgängig `list[dict]` mit Feldern `id, context_window, is_free, price_prompt, price_completion`. `CatalogModel` (Frontend) spiegelt dieselben Felder. `_available_models` + `validate_model` konsistent. `LlmProviderInfo.catalog: CatalogModel[]` durchgereicht bis `ModelPicker`.

**Reihenfolge-Hinweis:** T5 kann tsc-Fehler in ProviderForm auslösen (ungenutzte `models`); T7 behebt das. Im Plan vermerkt — bei Inline-Ausführung T7 direkt nach T5 ziehen falls tsc bricht.
