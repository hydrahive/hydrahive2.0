# Externe-Instanzen-Verwaltung (GUI) Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Admin kann externe Datamining-Instanzen (User + `external`-Agent + API-Key) in einem Schritt anlegen und verwalten — als Abschnitt auf der Federation-Seite.

**Architecture:** Backend-Orchestrierungs-Endpoints unter `/api/external-instances` (admin-only) legen User + Agent (`external=true`) + API-Key *für diesen User* in einem Rutsch an (nötig, da `api_keys.create` den Key an den Owner bindet). Keine neue Tabelle — der `external`-Marker am Agent ist die Einheit; Liste/Status werden aus Agent-Config + `agent_stats` + Sessions abgeleitet. Frontend ist ein dritter Abschnitt „Datamining-Instanzen" auf der bestehenden Federation-Seite, modelliert auf der existierenden „Clients"-Sektion.

**Tech Stack:** Python 3.12 / FastAPI / pytest (Backend), React + TypeScript + Vite (Frontend). Keine neuen Dependencies.

**Deployment:** Claude baut + testet lokal (`pytest` + `tsc`). **Till** deployt und testet im Browser.

**Abgrenzung:** `/federation/clients` (existiert) erzeugt admin-eigene Keys (`role=projektx`, AgentLink/Tailscale) für ProjektX. Dieser Pfad ist getrennt (eigener User+Agent, Datamining-Mirroring), nur co-lokalisiert auf derselben Seite.

---

## File Structure

**Backend:**
- Modify: `core/src/hydrahive/agents/config.py` (`create()` bekommt `external`-Param) + `core/src/hydrahive/agents/_config_utils.py`-Sicht (kein Change, `list_all` liefert das Feld automatisch aus der gespeicherten cfg).
- Modify: `core/src/hydrahive/api/routes/_agent_schemas.py` (`AgentCreate.external`) + `core/src/hydrahive/api/routes/agents.py` (`create_agent` reicht `external` durch).
- Create: `core/src/hydrahive/agents/external_instances.py` (Orchestrierung: create/list/delete/rotate).
- Create: `core/src/hydrahive/api/routes/external_instances.py` (4 Endpoints, admin).
- Modify: `core/src/hydrahive/api/main.py` (Router registrieren).
- Test: `core/tests/test_agent_external_field.py`, `core/tests/test_external_instances.py`, `core/tests/test_external_instances_api.py`.

**Frontend (Federation-Abschnitt):**
- Modify: `frontend/src/features/federation/types.ts` (`ExternalInstance`, `CreateInstanceResult`).
- Modify: `frontend/src/features/federation/api.ts` (`externalInstancesApi`).
- Create: `frontend/src/features/federation/_NewInstanceDialog.tsx`.
- Create: `frontend/src/features/federation/_DataminingInstancesSection.tsx`.
- Modify: `frontend/src/features/federation/FederationPage.tsx` (Abschnitt einhängen).

---

## Phase A — Backend

### Task 1: Agent-`external`-Feld

**Files:**
- Modify: `core/src/hydrahive/agents/config.py` (`create`, Z. 21-58)
- Modify: `core/src/hydrahive/api/routes/_agent_schemas.py` (`AgentCreate`)
- Modify: `core/src/hydrahive/api/routes/agents.py` (`create_agent`, Z. 88-104)
- Test: `core/tests/test_agent_external_field.py`

- [ ] **Step 1: Failing-Test schreiben**

```python
# core/tests/test_agent_external_field.py
from __future__ import annotations

MODEL = "claude-3-7-sonnet-20250219"  # im Test-Katalog gültig (wie conftest-Agent)


def test_create_agent_stores_external_flag(client, admin_headers):
    r = client.post("/api/agents",
                    json={"type": "master", "name": "ext-test", "llm_model": MODEL, "external": True},
                    headers=admin_headers)
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    got = client.get(f"/api/agents/{aid}", headers=admin_headers).json()
    assert got["external"] is True


def test_create_agent_defaults_external_false(client, admin_headers):
    r = client.post("/api/agents",
                    json={"type": "master", "name": "int-test", "llm_model": MODEL},
                    headers=admin_headers)
    assert r.status_code == 201, r.text
    assert r.json().get("external") is False
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd core && python3 -m pytest tests/test_agent_external_field.py -v`
Expected: FAIL — `external` fehlt in der Response (KeyError / None statt False/True)

- [ ] **Step 3: `external` in `agent_config.create` ergänzen**

In `core/src/hydrahive/agents/config.py` die Signatur von `create` um `external` erweitern (nach `system_prompt`):

```python
    system_prompt: str | None = None,
    external: bool = False,
) -> dict:
```

und im `cfg`-Dict (nach der `"status": "active", ...`-Zeile) ergänzen:

```python
        "status": "active", "created_at": now_iso(), "updated_at": now_iso(),
        "external": bool(external),
    }
```

- [ ] **Step 4: `AgentCreate` + Route durchreichen**

In `core/src/hydrahive/api/routes/_agent_schemas.py` zur Klasse `AgentCreate` hinzufügen:

```python
    external: bool = False
```

In `core/src/hydrahive/api/routes/agents.py` im `create_agent`-Aufruf von `agent_config.create(...)` ergänzen (letztes Argument):

```python
            system_prompt=req.system_prompt,
            external=req.external,
        )
```

- [ ] **Step 5: Test laufen lassen, PASS bestätigen**

Run: `cd core && python3 -m pytest tests/test_agent_external_field.py -v`
Expected: PASS (2 Tests)

- [ ] **Step 6: Gesamtsuite (Regression)**

Run: `cd core && python3 -m pytest -q`
Expected: PASS (default `external=False` ändert bestehende Agenten nicht)

- [ ] **Step 7: Commit**

```bash
git add core/src/hydrahive/agents/config.py core/src/hydrahive/api/routes/_agent_schemas.py core/src/hydrahive/api/routes/agents.py core/tests/test_agent_external_field.py
git commit -m "feat(agents): external-Marker am Agent (Config + AgentCreate + Route)"
```

---

### Task 2: Orchestrierungs-Service

**Files:**
- Create: `core/src/hydrahive/agents/external_instances.py`
- Test: `core/tests/test_external_instances.py`

- [ ] **Step 1: Failing-Test schreiben**

```python
# core/tests/test_external_instances.py
from __future__ import annotations

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.agents import external_instances as ei
from hydrahive.api.middleware import api_keys, users

MODEL = "claude-3-7-sonnet-20250219"


@pytest.fixture(autouse=True)
def _cleanup_external(client):
    # client → init_db + Env; nach jedem Test angelegte Instanzen entfernen,
    # damit der session-scoped Config-Dir andere Tests nicht verschmutzt.
    yield
    for inst in ei.list_instances():
        ei.delete_instance(inst["agent_id"])


def test_create_instance_makes_user_agent_key():
    res = ei.create_instance("joshua-test", MODEL)
    assert res["username"] == "joshua-test"
    assert res["api_key"].startswith("hhk_")
    agent = agent_config.get(res["agent_id"])
    assert agent["external"] is True
    assert agent["owner"] == "joshua-test"
    assert any(u["username"] == "joshua-test" for u in users.list_users())
    assert len(api_keys.list_keys(username="joshua-test")) == 1


def test_list_instances_only_external():
    ei.create_instance("ext-1", MODEL)
    names = [i["name"] for i in ei.list_instances()]
    assert "ext-1" in names
    assert "Test Agent" not in names  # conftest-Agent ist nicht external


def test_delete_instance_removes_everything():
    res = ei.create_instance("gone", MODEL)
    assert ei.delete_instance(res["agent_id"]) is True
    assert agent_config.get(res["agent_id"]) is None
    assert not any(u["username"] == "gone" for u in users.list_users())
    assert api_keys.list_keys(username="gone") == []


def test_rotate_key_replaces():
    res = ei.create_instance("rot", MODEL)
    old = api_keys.list_keys(username="rot")[0]["id"]
    new_key = ei.rotate_key(res["agent_id"])
    assert new_key.startswith("hhk_")
    keys = api_keys.list_keys(username="rot")
    assert len(keys) == 1 and keys[0]["id"] != old


def test_create_duplicate_name_raises():
    ei.create_instance("dup", MODEL)
    with pytest.raises(ValueError):
        ei.create_instance("dup", MODEL)
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd core && python3 -m pytest tests/test_external_instances.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'hydrahive.agents.external_instances'`

- [ ] **Step 3: Service schreiben**

```python
# core/src/hydrahive/agents/external_instances.py
"""Orchestriert externe Instanzen als Einheit: dedizierter User + Agent
(`external=true`) + API-Key (für diesen User). Keine eigene Tabelle — der
external-Marker am Agent ist die Einheit; Liste/Status werden abgeleitet."""
from __future__ import annotations

import secrets

from hydrahive.agents import config as agent_config
from hydrahive.agents._defaults import DEFAULT_MAX_TOKENS
from hydrahive.api.middleware import api_keys, users
from hydrahive.db import sessions as sessions_db, token_stats


def create_instance(name: str, llm_model: str) -> dict:
    """Legt User + external-Agent + API-Key an. Gibt den Key einmalig zurück.
    Rollt bei Teilfehler das bereits Angelegte zurück."""
    users.create(name, secrets.token_urlsafe(24), role="user")  # ValueError wenn User existiert
    try:
        agent = agent_config.create(
            agent_type="master", name=name, llm_model=llm_model, owner=name,
            external=True, temperature=0.7, max_tokens=DEFAULT_MAX_TOKENS, thinking_budget=0,
        )
    except Exception:
        users.delete(name)
        raise
    try:
        key = api_keys.create(name=f"{name}-hook", username=name, role="user")
    except Exception:
        agent_config.delete(agent["id"])
        users.delete(name)
        raise
    return {"username": name, "agent_id": agent["id"], "api_key": key}


def list_instances() -> list[dict]:
    out: list[dict] = []
    for a in agent_config.list_all():
        if not a.get("external"):
            continue
        owner = a.get("owner")
        keys = api_keys.list_keys(username=owner) if owner else []
        stats = token_stats.agent_stats(a["id"])
        recent = sessions_db.list_for_agent(a["id"], limit=1)
        out.append({
            "agent_id": a["id"],
            "name": a.get("name"),
            "username": owner,
            "key_count": len(keys),
            "session_count": stats.get("session_count", 0),
            "last_activity": recent[0].updated_at if recent else None,
        })
    return out


def delete_instance(agent_id: str) -> bool:
    a = agent_config.get(agent_id)
    if not a or not a.get("external"):
        return False
    owner = a.get("owner")
    agent_config.delete(agent_id)
    if owner:
        for k in api_keys.list_keys(username=owner):
            api_keys.delete(k["id"])
        users.delete(owner)
    return True


def rotate_key(agent_id: str) -> str | None:
    a = agent_config.get(agent_id)
    if not a or not a.get("external"):
        return None
    owner = a.get("owner")
    if not owner:
        return None
    for k in api_keys.list_keys(username=owner):
        api_keys.delete(k["id"])
    return api_keys.create(name=f"{a.get('name')}-hook", username=owner, role="user")
```

- [ ] **Step 4: Test laufen lassen, PASS bestätigen**

Run: `cd core && python3 -m pytest tests/test_external_instances.py -v`
Expected: PASS (5 Tests)

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/agents/external_instances.py core/tests/test_external_instances.py
git commit -m "feat(agents): external_instances-Orchestrierung (User+Agent+Key als Einheit)"
```

---

### Task 3: REST-Endpoints

**Files:**
- Create: `core/src/hydrahive/api/routes/external_instances.py`
- Modify: `core/src/hydrahive/api/main.py` (Router registrieren)
- Test: `core/tests/test_external_instances_api.py`

- [ ] **Step 1: Failing-Test schreiben**

```python
# core/tests/test_external_instances_api.py
from __future__ import annotations

import pytest

from hydrahive.agents import external_instances as ei

MODEL = "claude-3-7-sonnet-20250219"


@pytest.fixture(autouse=True)
def _cleanup_external(client):
    yield
    for inst in ei.list_instances():
        ei.delete_instance(inst["agent_id"])


def test_create_requires_admin(client, auth_headers):
    r = client.post("/api/external-instances",
                    json={"name": "x", "llm_model": MODEL}, headers=auth_headers)
    assert r.status_code == 403


def test_admin_create_and_list(client, admin_headers):
    r = client.post("/api/external-instances",
                    json={"name": "api-inst", "llm_model": MODEL}, headers=admin_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["api_key"].startswith("hhk_") and body["username"] == "api-inst"
    lst = client.get("/api/external-instances", headers=admin_headers).json()
    assert any(i["name"] == "api-inst" for i in lst)


def test_delete_instance(client, admin_headers):
    aid = client.post("/api/external-instances",
                      json={"name": "del-inst", "llm_model": MODEL}, headers=admin_headers).json()["agent_id"]
    assert client.delete(f"/api/external-instances/{aid}", headers=admin_headers).status_code == 204


def test_rotate_key(client, admin_headers):
    aid = client.post("/api/external-instances",
                      json={"name": "rot-inst", "llm_model": MODEL}, headers=admin_headers).json()["agent_id"]
    rk = client.post(f"/api/external-instances/{aid}/rotate-key", headers=admin_headers)
    assert rk.status_code == 200 and rk.json()["api_key"].startswith("hhk_")


def test_duplicate_name_409(client, admin_headers):
    client.post("/api/external-instances", json={"name": "dup-api", "llm_model": MODEL}, headers=admin_headers)
    r = client.post("/api/external-instances", json={"name": "dup-api", "llm_model": MODEL}, headers=admin_headers)
    assert r.status_code == 409
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd core && python3 -m pytest tests/test_external_instances_api.py -v`
Expected: FAIL — 404 (Route nicht registriert)

- [ ] **Step 3: Route schreiben**

```python
# core/src/hydrahive/api/routes/external_instances.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.agents import external_instances as ei
from hydrahive.api.middleware.auth import require_admin
from hydrahive.api.middleware.errors import coded

router = APIRouter(prefix="/api/external-instances", tags=["external-instances"])


class InstanceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    llm_model: str


@router.get("", dependencies=[Depends(require_admin)])
def list_external_instances() -> list[dict]:
    return ei.list_instances()


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_external_instance(req: InstanceCreate) -> dict:
    try:
        return ei.create_instance(req.name.strip(), req.llm_model)
    except ValueError:
        raise coded(status.HTTP_409_CONFLICT, "username_exists")


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
def delete_external_instance(agent_id: str) -> None:
    if not ei.delete_instance(agent_id):
        raise coded(status.HTTP_404_NOT_FOUND, "instance_not_found")


@router.post("/{agent_id}/rotate-key", dependencies=[Depends(require_admin)])
def rotate_external_instance_key(agent_id: str) -> dict:
    key = ei.rotate_key(agent_id)
    if key is None:
        raise coded(status.HTTP_404_NOT_FOUND, "instance_not_found")
    return {"api_key": key}
```

- [ ] **Step 4: Router in `api/main.py` registrieren**

In `core/src/hydrahive/api/main.py` neben den anderen Route-Imports `external_instances` ergänzen und neben den anderen `app.include_router(...)`-Aufrufen registrieren:

```python
from hydrahive.api.routes import external_instances
...
app.include_router(external_instances.router)
```

(Exakte Stelle: dieselbe Gruppe, in der z.B. `sessions`/`agents`/`federation` registriert werden — grep `include_router` in `api/main.py`.)

- [ ] **Step 5: Test laufen lassen, PASS bestätigen**

Run: `cd core && python3 -m pytest tests/test_external_instances_api.py -v`
Expected: PASS (5 Tests)

- [ ] **Step 6: Gesamtsuite**

Run: `cd core && python3 -m pytest -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add core/src/hydrahive/api/routes/external_instances.py core/src/hydrahive/api/main.py core/tests/test_external_instances_api.py
git commit -m "feat(api): /api/external-instances Endpoints (create/list/delete/rotate, admin)"
```

---

## Phase B — Frontend (Federation-Abschnitt)

> Frontend-Verifikation: `tsc`/Build grün + Tills Browser-Test (das Projekt hat keine Component-Test-Suite — keine erfinden).

### Task 4: API-Client + Typen erweitern

**Files:**
- Modify: `frontend/src/features/federation/types.ts`
- Modify: `frontend/src/features/federation/api.ts`

- [ ] **Step 1: Typen ergänzen**

Am Ende von `frontend/src/features/federation/types.ts`:

```typescript
export interface ExternalInstance {
  agent_id: string
  name: string
  username: string
  key_count: number
  session_count: number
  last_activity: string | null
}

export interface CreateInstanceResult {
  username: string
  agent_id: string
  api_key: string
}
```

- [ ] **Step 2: API-Client ergänzen**

In `frontend/src/features/federation/api.ts` den Typ-Import erweitern und `externalInstancesApi` ergänzen:

```typescript
import type {
  A2ACard, ClientConnection, CreateClientResult, Workstation,
  ExternalInstance, CreateInstanceResult,
} from "./types"

// ... bestehende federationApi / clientsApi unverändert ...

export const externalInstancesApi = {
  list: (): Promise<ExternalInstance[]> =>
    api.get("/external-instances"),

  create: (name: string, llm_model: string): Promise<CreateInstanceResult> =>
    api.post("/external-instances", { name, llm_model }),

  delete: (agentId: string): Promise<void> =>
    api.delete(`/external-instances/${agentId}`),

  rotateKey: (agentId: string): Promise<{ api_key: string }> =>
    api.post(`/external-instances/${agentId}/rotate-key`, {}),
}
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: keine neuen Fehler in `federation/`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/federation/types.ts frontend/src/features/federation/api.ts
git commit -m "feat(fe): externalInstancesApi + Typen (Federation)"
```

---

### Task 5: Dialog + Abschnitt-Komponente

**Files:**
- Create: `frontend/src/features/federation/_NewInstanceDialog.tsx`
- Create: `frontend/src/features/federation/_DataminingInstancesSection.tsx`

- [ ] **Step 1: Wizard-Dialog schreiben** (modelliert auf `_NewClientDialog.tsx`)

```tsx
// frontend/src/features/federation/_NewInstanceDialog.tsx
import { useState } from "react"
import { Copy, X } from "lucide-react"
import { externalInstancesApi } from "./api"
import type { CreateInstanceResult } from "./types"

interface Props {
  onClose: () => void
  onCreated: () => void
}

function configBlock(r: CreateInstanceResult): string {
  const base = window.location.origin
  return [
    `HH_BASE_URL=${base}`,
    `HH_API_KEY=${r.api_key}`,
    `HH_AGENT_ID=${r.agent_id}`,
    `HH_VERIFY_SSL=0   # nur für self-signed LAN`,
  ].join("\n")
}

export function NewInstanceDialog({ onClose, onCreated }: Props) {
  const [name, setName] = useState("")
  const [model, setModel] = useState("claude-opus-4-8")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CreateInstanceResult | null>(null)
  const [error, setError] = useState("")

  async function handleCreate() {
    if (!name.trim()) return
    setLoading(true)
    setError("")
    try {
      const data = await externalInstancesApi.create(name.trim(), model.trim())
      setResult(data)
      onCreated()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Erstellen")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-lg rounded-2xl border border-white/[8%] bg-zinc-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-zinc-100">Neue Datamining-Instanz</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 transition-colors">
            <X size={16} />
          </button>
        </div>

        {!result ? (
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-zinc-400 mb-1.5">Instanz-Name</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleCreate()}
                placeholder="z.B. joshua, claude-laptop"
                className="w-full rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1.5">Modell</label>
              <input
                type="text"
                value={model}
                onChange={e => setModel(e.target.value)}
                className="w-full rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
              />
            </div>
            {error && <p className="text-xs text-red-400">{error}</p>}
            <p className="text-xs text-zinc-500">
              Legt User + Agent + API-Key an. Der Key wird nur einmalig angezeigt.
            </p>
            <div className="flex justify-end gap-2 pt-1">
              <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 transition-colors">
                Abbrechen
              </button>
              <button
                onClick={handleCreate}
                disabled={loading || !name.trim()}
                className="px-4 py-1.5 rounded-lg text-sm bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
              >
                {loading ? "Erstelle…" : "Instanz anlegen"}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs text-emerald-300">
              Instanz <strong>{result.username}</strong> angelegt. Kopiere den Block jetzt —
              der API-Key wird nicht erneut angezeigt.
            </div>
            <pre className="rounded-lg border border-white/[6%] bg-zinc-800/60 p-3 text-xs font-mono text-zinc-300 whitespace-pre-wrap break-all">{configBlock(result)}</pre>
            <div className="flex justify-end gap-2 pt-1">
              <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 transition-colors">
                Schließen
              </button>
              <button
                onClick={() => navigator.clipboard.writeText(configBlock(result))}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm bg-violet-600 hover:bg-violet-500 text-white transition-colors"
              >
                <Copy size={13} />
                Config kopieren
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Abschnitt-Komponente schreiben** (modelliert auf `_ClientConnectionsSection.tsx`)

```tsx
// frontend/src/features/federation/_DataminingInstancesSection.tsx
import { useEffect, useState } from "react"
import { Pickaxe, Plus, RefreshCw, Trash2 } from "lucide-react"
import { externalInstancesApi } from "./api"
import type { ExternalInstance } from "./types"
import { NewInstanceDialog } from "./_NewInstanceDialog"

function formatDate(iso: string | null) {
  if (!iso) return "—"
  try {
    return new Date(iso).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" })
  } catch {
    return iso
  }
}

export function DataminingInstancesSection() {
  const [instances, setInstances] = useState<ExternalInstance[]>([])
  const [loading, setLoading] = useState(true)
  const [showNew, setShowNew] = useState(false)

  async function load() {
    try {
      setInstances(await externalInstancesApi.list())
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(inst: ExternalInstance) {
    if (!confirm(`Instanz "${inst.name}" löschen? User, Agent und API-Key werden entfernt.`)) return
    await externalInstancesApi.delete(inst.agent_id).catch(() => {})
    load()
  }

  async function handleRotate(inst: ExternalInstance) {
    if (!confirm(`Key für "${inst.name}" rotieren? Der alte Key wird ungültig.`)) return
    try {
      const { api_key } = await externalInstancesApi.rotateKey(inst.agent_id)
      window.prompt("Neuer API-Key (einmalig — jetzt kopieren):", api_key)
    } catch { /* ignore */ }
    load()
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Pickaxe size={15} className="text-violet-400" />
          <span className="text-sm font-medium text-zinc-200">Datamining-Instanzen</span>
          <span className="text-xs text-zinc-600 ml-1">
            Externe Claude-Code-Instanzen, die live ins Datamining spiegeln
          </span>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-zinc-100 border border-white/[6%] transition-colors"
        >
          <Plus size={12} />
          Neue Instanz
        </button>
      </div>

      {loading ? (
        <div className="text-xs text-zinc-600 py-4 text-center">Lade…</div>
      ) : instances.length === 0 ? (
        <div className="rounded-xl border border-white/[4%] bg-zinc-950/30 py-8 text-center">
          <Pickaxe size={24} className="text-zinc-700 mx-auto mb-2" />
          <p className="text-xs text-zinc-600">Noch keine Datamining-Instanzen</p>
        </div>
      ) : (
        <div className="space-y-1">
          {instances.map(inst => (
            <div key={inst.agent_id}
                 className="flex items-center justify-between rounded-lg border border-white/[5%] bg-zinc-900/60 px-3 py-2.5">
              <div className="flex items-center gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/70" />
                <div>
                  <span className="text-sm text-zinc-200">{inst.name}</span>
                  <span className="ml-2 text-xs text-zinc-600">
                    · {inst.session_count} Sessions · zuletzt {formatDate(inst.last_activity)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => handleRotate(inst)}
                        className="p-1 text-zinc-600 hover:text-violet-400 transition-colors" title="API-Key rotieren">
                  <RefreshCw size={13} />
                </button>
                <button onClick={() => handleDelete(inst)}
                        className="p-1 text-zinc-600 hover:text-red-400 transition-colors" title="Instanz löschen">
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showNew && (
        <NewInstanceDialog
          onClose={() => setShowNew(false)}
          onCreated={() => { setShowNew(false); load() }}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: keine neuen Fehler.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/federation/_NewInstanceDialog.tsx frontend/src/features/federation/_DataminingInstancesSection.tsx
git commit -m "feat(fe): Datamining-Instanzen-Abschnitt + Wizard (Federation)"
```

---

### Task 6: In die Federation-Seite einhängen

**Files:**
- Modify: `frontend/src/features/federation/FederationPage.tsx`

- [ ] **Step 1: Abschnitt einhängen**

In `frontend/src/features/federation/FederationPage.tsx` den Import ergänzen:

```tsx
import { DataminingInstancesSection } from "./_DataminingInstancesSection"
```

und die Komponente unterhalb von `<ClientConnectionsSection />` rendern (gleiche Verschachtelung/Abstände wie die bestehenden Abschnitte — Datei vorher lesen und das Muster spiegeln):

```tsx
<ClientConnectionsSection />
<DataminingInstancesSection />
```

- [ ] **Step 2: Typecheck + Build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: Build grün.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/federation/FederationPage.tsx
git commit -m "feat(fe): Datamining-Instanzen-Abschnitt auf der Federation-Seite einhängen"
```

---

## Manuelle Verifikation (Till, nach Deploy)

1. Federation-Seite öffnen → dritter Abschnitt „Datamining-Instanzen" sichtbar.
2. „Neue Instanz" → Name + Modell → Config-Block erscheint einmalig mit `HH_API_KEY`/`HH_AGENT_ID`.
3. Block auf eine Claude-Code-Maschine kopieren, Hook (`hooks/datamining-sync/`) verdrahten → eine Runde → Instanz zeigt Session-Count/Last-Activity.
4. Key rotieren → alter Key ungültig. Instanz löschen → User+Agent+Key weg.

---

## Self-Review

**Spec-Coverage (gegen SPEC „Externe Instanzen — Verwaltung (GUI)"):**
- `POST /api/external-instances` (User+Agent+Key, einmaliger Key) → Task 2+3. ✓
- `GET /api/external-instances` (Liste + agent_stats-Aktivität) → Task 2 (`list_instances`) + Task 3. ✓
- `DELETE …/{agent_id}` (Agent+User+Keys) → Task 2+3. ✓
- `POST …/{agent_id}/rotate-key` → Task 2+3. ✓
- Agent-`external`-Marker → Task 1. ✓
- Frontend als Federation-Abschnitt, Wizard zeigt Config einmalig → Task 4-6. ✓
- Abgrenzung zu `/federation/clients` → im Plan-Header dokumentiert, separate Endpoints. ✓

**Platzhalter:** keine — jeder Code-Step enthält vollständigen Code; einzige „Datei vorher lesen"-Hinweise betreffen das Einhängen in bestehende Dateien (`main.py` include_router, `FederationPage.tsx`), wo das exakte Umfeld variiert.

**Typ-Konsistenz:** `external_instances.create_instance/list_instances/delete_instance/rotate_key`-Signaturen identisch in Service (Task 2), Route (Task 3) und Tests. `ExternalInstance`/`CreateInstanceResult`-Felder identisch in types.ts (Task 4), API (Task 4) und Komponenten (Task 5). `agent_config.create(..., external=...)` (Task 1) == Aufruf in `create_instance` (Task 2).

**Bewusste Grenzen (YAGNI):** keine Frontend-Unit-Tests (Projekt hat keine Suite), kein eigener Nav-Eintrag (Co-Location), keine Registry-Tabelle (Marker genügt), Key-Rotation zeigt den Key per `window.prompt` (schlicht, einmalig) statt eigenem Modal.
