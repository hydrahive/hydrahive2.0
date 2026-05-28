# Digitale Patientenakte Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FHIR R4 JSON aus der TK-App importieren und als vollständigen digitalen Aktenschrank in HydraHive anzeigen — mit KI-Assistent der Fragen zur Akte beantwortet.

**Architecture:** Generische `fhir_resources`-Tabelle (user_id + resource_type + resource_id + JSON), Import per FHIR Bundle Upload mit Upsert-Semantik, Agent-Tool `query_fhir_data` für KI-Zugriff, Frontend-Rebuild der Health-Sektion mit Sidebar-Navigation.

**Tech Stack:** Python 3.12 + FastAPI (Backend), SQLite (Storage), React + TypeScript (Frontend), FHIR R4 (Datenformat)

---

## Datei-Übersicht

| Aktion | Datei |
|---|---|
| Erstellen | `core/src/hydrahive/db/migrations/021_fhir_resources.sql` |
| Erstellen | `core/src/hydrahive/db/fhir.py` |
| Erstellen | `core/src/hydrahive/api/routes/fhir.py` |
| Ändern | `core/src/hydrahive/api/main.py` |
| Erstellen | `core/src/hydrahive/tools/fhir_data.py` |
| Ändern | `core/src/hydrahive/tools/__init__.py` |
| Erstellen | `core/tests/test_fhir_import_smoke.py` |
| Erstellen | `core/tests/test_fhir_query_smoke.py` |
| Ersetzen | `frontend/src/features/health/HealthPage.tsx` |
| Erstellen | `frontend/src/features/health/HealthSidebar.tsx` |
| Erstellen | `frontend/src/features/health/KiFloatingButton.tsx` |
| Erstellen | `frontend/src/features/health/views/UebersichtView.tsx` |
| Erstellen | `frontend/src/features/health/views/ZeitstrahlView.tsx` |
| Erstellen | `frontend/src/features/health/views/DiagnosenView.tsx` |
| Erstellen | `frontend/src/features/health/views/MedikamenteView.tsx` |
| Erstellen | `frontend/src/features/health/views/LaborwerteView.tsx` |
| Erstellen | `frontend/src/features/health/views/SimpleListView.tsx` |
| Erstellen | `frontend/src/features/health/views/KiAssistentView.tsx` |
| Erstellen | `frontend/src/features/health/components/ResourceTable.tsx` |
| Erstellen | `frontend/src/features/health/components/FhirImportButton.tsx` |
| Ändern | `frontend/src/features/health/api.ts` |

---

## Task 1: DB-Migration

**Files:**
- Create: `core/src/hydrahive/db/migrations/021_fhir_resources.sql`

- [ ] **Schritt 1: Migration anlegen**

```sql
-- 021_fhir_resources.sql
CREATE TABLE IF NOT EXISTS fhir_resources (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id   TEXT NOT NULL,
    resource_json TEXT NOT NULL,
    imported_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fhir_unique
    ON fhir_resources(user_id, resource_type, resource_id);

CREATE INDEX IF NOT EXISTS idx_fhir_user_type
    ON fhir_resources(user_id, resource_type);

CREATE INDEX IF NOT EXISTS idx_fhir_user_id
    ON fhir_resources(user_id);
```

- [ ] **Schritt 2: Migration testen**

```bash
cd /home/till/claudeneu
python3 -c "
from core.src.hydrahive.db.connection import db
from core.src.hydrahive.db import init_db
import os, tempfile
with tempfile.TemporaryDirectory() as d:
    os.environ['HH_DATA_DIR'] = d + '/data'
    os.makedirs(d + '/data', exist_ok=True)
    init_db()
    with db() as conn:
        rows = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='fhir_resources'\").fetchall()
        print('OK' if rows else 'FEHLER')
"
```
Erwartete Ausgabe: `OK`

- [ ] **Schritt 3: Commit**

```bash
git add core/src/hydrahive/db/migrations/021_fhir_resources.sql
git commit -m "feat(fhir): Migration 021 — fhir_resources Tabelle"
```

---

## Task 2: db/fhir.py

**Files:**
- Create: `core/src/hydrahive/db/fhir.py`

- [ ] **Schritt 1: Datei anlegen**

```python
"""FHIR-Ressourcen — Datenbankoperationen."""
from __future__ import annotations

import json
from typing import Any

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

# FHIR resourceType → Sidebar-Kategorie
RESOURCE_LABELS: dict[str, str] = {
    "Condition": "Diagnosen",
    "MedicationRequest": "Medikamente",
    "MedicationStatement": "Medikamente",
    "Observation": "Laborwerte",
    "AllergyIntolerance": "Allergien",
    "Immunization": "Impfungen",
    "Procedure": "Eingriffe",
    "Encounter": "Arztbesuche",
    "DiagnosticReport": "Befunde",
    "DocumentReference": "Dokumente",
    "Patient": "Stammdaten",
}


def upsert_bundle(bundle: dict, user_id: str) -> dict:
    """Importiert ein FHIR Bundle. Gibt Import-Statistik zurück."""
    if bundle.get("resourceType") != "Bundle":
        raise ValueError("Kein gültiges FHIR Bundle")

    entries = bundle.get("entry", [])
    imported = updated = errors = 0

    with db() as conn:
        for entry in entries:
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType", "")
            resource_id = resource.get("id", "")
            if not resource_type or not resource_id:
                errors += 1
                continue
            try:
                exists = conn.execute(
                    "SELECT id FROM fhir_resources WHERE user_id=? AND resource_type=? AND resource_id=?",
                    (user_id, resource_type, resource_id),
                ).fetchone()
                if exists:
                    conn.execute(
                        "UPDATE fhir_resources SET resource_json=?, imported_at=? WHERE user_id=? AND resource_type=? AND resource_id=?",
                        (json.dumps(resource), now_iso(), user_id, resource_type, resource_id),
                    )
                    updated += 1
                else:
                    conn.execute(
                        "INSERT INTO fhir_resources (id, user_id, resource_type, resource_id, resource_json, imported_at) VALUES (?,?,?,?,?,?)",
                        (uuid7(), user_id, resource_type, resource_id, json.dumps(resource), now_iso()),
                    )
                    imported += 1
            except Exception:
                errors += 1

    return {"imported": imported, "updated": updated, "errors": errors}


def query_by_type(user_id: str, resource_type: str) -> list[dict]:
    """Gibt alle Ressourcen eines Typs für einen User zurück."""
    with db() as conn:
        rows = conn.execute(
            "SELECT resource_json, imported_at FROM fhir_resources WHERE user_id=? AND resource_type=? ORDER BY imported_at DESC",
            (user_id, resource_type),
        ).fetchall()
    return [{"resource": json.loads(r["resource_json"]), "imported_at": r["imported_at"]} for r in rows]


def summary(user_id: str) -> dict:
    """Gibt Zähler pro Ressourcentyp zurück."""
    with db() as conn:
        rows = conn.execute(
            "SELECT resource_type, COUNT(*) as count FROM fhir_resources WHERE user_id=? GROUP BY resource_type",
            (user_id,),
        ).fetchall()
    return {r["resource_type"]: r["count"] for r in rows}


def timeline(user_id: str) -> list[dict]:
    """Gibt alle Ressourcen chronologisch sortiert zurück (neueste zuerst)."""
    with db() as conn:
        rows = conn.execute(
            "SELECT resource_type, resource_json, imported_at FROM fhir_resources WHERE user_id=? ORDER BY imported_at DESC",
            (user_id,),
        ).fetchall()
    return [
        {
            "resource_type": r["resource_type"],
            "label": RESOURCE_LABELS.get(r["resource_type"], r["resource_type"]),
            "resource": json.loads(r["resource_json"]),
            "imported_at": r["imported_at"],
        }
        for r in rows
    ]


def query_fulltext(user_id: str, search: str, resource_types: list[str] | None = None) -> list[dict]:
    """Volltextsuche im resource_json für den KI-Assistenten."""
    with db() as conn:
        if resource_types:
            placeholders = ",".join("?" * len(resource_types))
            rows = conn.execute(
                f"SELECT resource_type, resource_json FROM fhir_resources WHERE user_id=? AND resource_type IN ({placeholders}) AND resource_json LIKE ? ORDER BY imported_at DESC LIMIT 50",
                (user_id, *resource_types, f"%{search}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT resource_type, resource_json FROM fhir_resources WHERE user_id=? AND resource_json LIKE ? ORDER BY imported_at DESC LIMIT 50",
                (user_id, f"%{search}%"),
            ).fetchall()
    return [{"resource_type": r["resource_type"], "resource": json.loads(r["resource_json"])} for r in rows]
```

- [ ] **Schritt 2: Commit**

```bash
git add core/src/hydrahive/db/fhir.py
git commit -m "feat(fhir): db/fhir.py — upsert_bundle, query_by_type, summary, timeline"
```

---

## Task 3: Import-API + Router

**Files:**
- Create: `core/src/hydrahive/api/routes/fhir.py`
- Modify: `core/src/hydrahive/api/main.py`

- [ ] **Schritt 1: Route anlegen**

```python
"""FHIR-Patientenakte — Import und Abfrage."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from hydrahive.api.middleware.auth import require_auth
from hydrahive.db import fhir as fhir_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fhir", tags=["fhir"])


@router.post("/import")
async def import_bundle(
    bundle: dict,
    user: Annotated[dict, Depends(require_auth)],
) -> dict:
    """FHIR Bundle importieren (Upsert-Semantik)."""
    try:
        result = fhir_db.upsert_bundle(bundle, user_id=user["username"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_fhir_bundle", "message": str(exc)})
    logger.info("fhir_import user=%s imported=%d updated=%d errors=%d",
                user["username"], result["imported"], result["updated"], result["errors"])
    return result


@router.get("/resources/{resource_type}")
async def get_resources(
    resource_type: str,
    user: Annotated[dict, Depends(require_auth)],
) -> dict:
    """Alle Ressourcen eines Typs für den eingeloggten User."""
    resources = fhir_db.query_by_type(user_id=user["username"], resource_type=resource_type)
    return {"resource_type": resource_type, "count": len(resources), "resources": resources}


@router.get("/summary")
async def get_summary(
    user: Annotated[dict, Depends(require_auth)],
) -> dict:
    """Zähler pro Ressourcentyp."""
    return fhir_db.summary(user_id=user["username"])


@router.get("/timeline")
async def get_timeline(
    user: Annotated[dict, Depends(require_auth)],
) -> dict:
    """Alle Ressourcen chronologisch."""
    entries = fhir_db.timeline(user_id=user["username"])
    return {"count": len(entries), "entries": entries}
```

- [ ] **Schritt 2: Router in main.py registrieren**

In `core/src/hydrahive/api/main.py` nach den bestehenden Imports ergänzen:

```python
from hydrahive.api.routes.fhir import router as fhir_router
```

Und in der Liste der `app.include_router(...)` Aufrufe hinzufügen:

```python
app.include_router(fhir_router)
```

- [ ] **Schritt 3: Commit**

```bash
git add core/src/hydrahive/api/routes/fhir.py core/src/hydrahive/api/main.py
git commit -m "feat(fhir): Import- und Abfrage-Endpoints /api/fhir/*"
```

---

## Task 4: Import-Tests

**Files:**
- Create: `core/tests/test_fhir_import_smoke.py`

- [ ] **Schritt 1: Test schreiben**

```python
"""Smoke-Tests für FHIR-Import und Abfrage."""
from __future__ import annotations

import pytest


def _bundle(resources: list[dict]) -> dict:
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": r} for r in resources],
    }


def _condition(resource_id: str, code: str, display: str) -> dict:
    return {
        "resourceType": "Condition",
        "id": resource_id,
        "code": {"coding": [{"code": code, "display": display}]},
        "clinicalStatus": {"coding": [{"code": "active"}]},
    }


def test_import_bundle(client, auth_headers):
    bundle = _bundle([_condition("c1", "I10", "Hypertonie"), _condition("c2", "E11", "Diabetes")])
    resp = client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 2
    assert data["updated"] == 0
    assert data["errors"] == 0


def test_import_merge_upsert(client, auth_headers):
    bundle = _bundle([_condition("c1", "I10", "Hypertonie")])
    client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    # Zweiter Import — selbe ID, aktualisierter Display
    bundle2 = _bundle([_condition("c1", "I10", "Arterielle Hypertonie")])
    resp = client.post("/api/fhir/import", json=bundle2, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 0
    assert data["updated"] == 1


def test_import_invalid_bundle(client, auth_headers):
    resp = client.post("/api/fhir/import", json={"resourceType": "Patient"}, headers=auth_headers)
    assert resp.status_code == 422


def test_get_resources(client, auth_headers):
    bundle = _bundle([_condition("c1", "I10", "Hypertonie")])
    client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    resp = client.get("/api/fhir/resources/Condition", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_user_isolation(client, auth_headers, admin_headers):
    bundle = _bundle([_condition("c-private", "I10", "Privat")])
    client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    resp = client.get("/api/fhir/resources/Condition", headers=admin_headers)
    ids = [e["resource"]["id"] for e in resp.json()["resources"]]
    assert "c-private" not in ids


def test_summary(client, auth_headers):
    bundle = _bundle([_condition("c1", "I10", "Hypertonie")])
    client.post("/api/fhir/import", json=bundle, headers=auth_headers)
    resp = client.get("/api/fhir/summary", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json().get("Condition", 0) >= 1
```

- [ ] **Schritt 2: Tests ausführen**

```bash
cd /home/till/claudeneu
.venv/bin/pytest core/tests/test_fhir_import_smoke.py -v
```

Erwartete Ausgabe: 6 passed

- [ ] **Schritt 3: Commit**

```bash
git add core/tests/test_fhir_import_smoke.py
git commit -m "test(fhir): Import-Smoke-Tests — Upsert, Isolation, Validation"
```

---

## Task 5: Agent-Tool fhir_data.py

**Files:**
- Create: `core/src/hydrahive/tools/fhir_data.py`
- Modify: `core/src/hydrahive/tools/__init__.py`

- [ ] **Schritt 1: Tool anlegen**

```python
"""query_fhir_data — KI-Tool für Zugriff auf die FHIR-Patientenakte."""
from __future__ import annotations

import json

from hydrahive.db import fhir as fhir_db
from hydrahive.tools.base import Tool, ToolContext, ToolResult

_DESCRIPTION = (
    "Liest Daten aus der digitalen Patientenakte (FHIR R4 Format, importiert aus der TK-App). "
    "Enthält Diagnosen, Medikamente, Laborwerte, Allergien, Impfungen, Eingriffe, "
    "Arztbesuche, Befunde und Dokumente. "
    "Nutze dieses Tool um Fragen zur Krankengeschichte zu beantworten. "
    "Stelle keine Diagnosen — erkläre nur was in der Akte steht. "
    "Verweise bei medizinischen Unsicherheiten auf den behandelnden Arzt."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "resource_types": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Optional: Welche Ressourcentypen abfragen. "
                "Mögliche Werte: Condition, MedicationRequest, MedicationStatement, "
                "Observation, AllergyIntolerance, Immunization, Procedure, "
                "Encounter, DiagnosticReport, DocumentReference, Patient. "
                "Leer lassen für alle Typen."
            ),
        },
        "search_text": {
            "type": "string",
            "description": "Optional: Volltextsuche im JSON (z.B. 'HbA1c', 'Ramipril', 'Kardiologie').",
        },
    },
}


def _format_resource(r: dict) -> str:
    """Wandelt eine FHIR-Ressource in lesbaren Text um."""
    rt = r.get("resourceType", "")
    rid = r.get("id", "")

    if rt == "Condition":
        code = r.get("code", {})
        codings = code.get("coding", [{}])
        display = codings[0].get("display", code.get("text", "Unbekannt"))
        icd = codings[0].get("code", "")
        status = r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")
        onset = r.get("onsetDateTime", r.get("onsetString", ""))
        return f"Diagnose [{rid}]: {display} (ICD: {icd}, Status: {status}, Beginn: {onset})"

    if rt in ("MedicationRequest", "MedicationStatement"):
        med = r.get("medicationCodeableConcept", r.get("medicationReference", {}))
        name = med.get("text", med.get("display", "Unbekannt")) if isinstance(med, dict) else str(med)
        status = r.get("status", "")
        return f"Medikament [{rid}]: {name} (Status: {status})"

    if rt == "Observation":
        code = r.get("code", {}).get("text", r.get("code", {}).get("coding", [{}])[0].get("display", ""))
        value = r.get("valueQuantity", {})
        val_str = f"{value.get('value', '')} {value.get('unit', '')}".strip() if value else r.get("valueString", "")
        date = r.get("effectiveDateTime", "")
        return f"Laborwert [{rid}]: {code} = {val_str} (am {date})"

    if rt == "AllergyIntolerance":
        substance = r.get("code", {}).get("text", "Unbekannt")
        return f"Allergie [{rid}]: {substance}"

    if rt == "Immunization":
        vaccine = r.get("vaccineCode", {}).get("text", "Unbekannt")
        date = r.get("occurrenceDateTime", "")
        return f"Impfung [{rid}]: {vaccine} (am {date})"

    if rt == "Encounter":
        class_ = r.get("class", {}).get("display", "")
        date = r.get("period", {}).get("start", "")
        return f"Arztbesuch [{rid}]: {class_} (am {date})"

    # Fallback: JSON-Kurzform
    return f"{rt} [{rid}]: {json.dumps(r)[:200]}"


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    user_id = ctx.user_id
    if not user_id:
        return ToolResult.fail("Kein User-Kontext verfügbar.")

    resource_types: list[str] | None = args.get("resource_types") or None
    search_text: str = (args.get("search_text") or "").strip()

    try:
        if search_text:
            resources = fhir_db.query_fulltext(user_id, search_text, resource_types)
            entries = [r["resource"] for r in resources]
        elif resource_types:
            entries = []
            for rt in resource_types:
                for row in fhir_db.query_by_type(user_id, rt):
                    entries.append(row["resource"])
        else:
            entries = [row["resource"] for row in fhir_db.timeline(user_id)]

    except Exception as exc:
        return ToolResult.fail(f"FHIR-DB-Fehler: {exc}")

    if not entries:
        scope = f" für '{search_text}'" if search_text else ""
        return ToolResult.ok({"message": f"Keine FHIR-Daten gefunden{scope}.", "count": 0})

    lines = [_format_resource(e) for e in entries[:100]]
    return ToolResult.ok({
        "count": len(entries),
        "data": "\n".join(lines),
    })


TOOL = Tool(
    name="query_fhir_data",
    description=_DESCRIPTION,
    schema=_SCHEMA,
    execute=_execute,
    category="personal",
)
```

- [ ] **Schritt 2: Tool in Registry registrieren**

In `core/src/hydrahive/tools/__init__.py` ergänzen:

```python
from hydrahive.tools import (
    ...
    fhir_data,          # ← neu hinzufügen
    ...
)
```

Und in der `REGISTRY`-Liste `fhir_data.TOOL` ergänzen (gleiche Stelle wie die anderen Tools).

- [ ] **Schritt 3: Commit**

```bash
git add core/src/hydrahive/tools/fhir_data.py core/src/hydrahive/tools/__init__.py
git commit -m "feat(fhir): Agent-Tool query_fhir_data für KI-Patientenakte"
```

---

## Task 6: Tool-Tests

**Files:**
- Create: `core/tests/test_fhir_query_smoke.py`

- [ ] **Schritt 1: Test schreiben**

```python
"""Smoke-Tests für query_fhir_data Agent-Tool."""
from __future__ import annotations

import asyncio
import pytest

from hydrahive.butler.models import TriggerEvent


def _run(coro):
    return asyncio.run(coro)


def _insert_test_data(client, auth_headers):
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": {
                "resourceType": "Condition", "id": "c1",
                "code": {"coding": [{"code": "I10", "display": "Hypertonie"}]},
                "clinicalStatus": {"coding": [{"code": "active"}]},
            }},
            {"resource": {
                "resourceType": "Observation", "id": "o1",
                "code": {"text": "HbA1c"},
                "valueQuantity": {"value": 6.2, "unit": "%"},
                "effectiveDateTime": "2024-03-01",
            }},
        ],
    }
    client.post("/api/fhir/import", json=bundle, headers=auth_headers)


def test_query_all_types(client, auth_headers):
    _insert_test_data(client, auth_headers)
    from hydrahive.tools.fhir_data import TOOL
    from hydrahive.tools.base import ToolContext
    ctx = ToolContext(user_id="testuser", session_id="smoke")
    result = _run(TOOL.execute({}, ctx))
    assert result.ok
    assert result.data["count"] >= 2


def test_query_by_type(client, auth_headers):
    _insert_test_data(client, auth_headers)
    from hydrahive.tools.fhir_data import TOOL
    from hydrahive.tools.base import ToolContext
    ctx = ToolContext(user_id="testuser", session_id="smoke")
    result = _run(TOOL.execute({"resource_types": ["Condition"]}, ctx))
    assert result.ok
    assert "Hypertonie" in result.data["data"]


def test_query_fulltext(client, auth_headers):
    _insert_test_data(client, auth_headers)
    from hydrahive.tools.fhir_data import TOOL
    from hydrahive.tools.base import ToolContext
    ctx = ToolContext(user_id="testuser", session_id="smoke")
    result = _run(TOOL.execute({"search_text": "HbA1c"}, ctx))
    assert result.ok
    assert result.data["count"] >= 1


def test_query_empty_returns_message(client, auth_headers):
    from hydrahive.tools.fhir_data import TOOL
    from hydrahive.tools.base import ToolContext
    ctx = ToolContext(user_id="testuser", session_id="smoke")
    result = _run(TOOL.execute({"search_text": "xyznotexistent123"}, ctx))
    assert result.ok
    assert "Keine" in result.data["message"]
```

- [ ] **Schritt 2: Tests ausführen**

```bash
cd /home/till/claudeneu
.venv/bin/pytest core/tests/test_fhir_query_smoke.py -v
```

Erwartete Ausgabe: 4 passed

- [ ] **Schritt 3: Commit**

```bash
git add core/tests/test_fhir_query_smoke.py
git commit -m "test(fhir): Tool-Smoke-Tests — query_fhir_data alle Pfade"
```

---

## Task 7: Frontend — api.ts erweitern

**Files:**
- Modify: `frontend/src/features/health/api.ts`

- [ ] **Schritt 1: FHIR-API-Funktionen ergänzen**

Am Ende von `frontend/src/features/health/api.ts` hinzufügen:

```typescript
// ─── FHIR Patientenakte ────────────────────────────────────────────────────

export interface FhirImportResult {
  imported: number
  updated: number
  errors: number
}

export interface FhirResource {
  resource: Record<string, unknown>
  imported_at: string
}

export interface FhirResourcesResponse {
  resource_type: string
  count: number
  resources: FhirResource[]
}

export interface FhirSummary {
  [resourceType: string]: number
}

export interface FhirTimelineEntry {
  resource_type: string
  label: string
  resource: Record<string, unknown>
  imported_at: string
}

export const fhirApi = {
  async importBundle(file: File): Promise<FhirImportResult> {
    const text = await file.text()
    const bundle = JSON.parse(text)
    const res = await fetch("/api/fhir/import", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("hh_token") ?? ""}`,
      },
      body: JSON.stringify(bundle),
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getResources(resourceType: string): Promise<FhirResourcesResponse> {
    const res = await fetch(`/api/fhir/resources/${resourceType}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("hh_token") ?? ""}` },
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getSummary(): Promise<FhirSummary> {
    const res = await fetch("/api/fhir/summary", {
      headers: { Authorization: `Bearer ${localStorage.getItem("hh_token") ?? ""}` },
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },

  async getTimeline(): Promise<{ count: number; entries: FhirTimelineEntry[] }> {
    const res = await fetch("/api/fhir/timeline", {
      headers: { Authorization: `Bearer ${localStorage.getItem("hh_token") ?? ""}` },
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  },
}
```

- [ ] **Schritt 2: Commit**

```bash
git add frontend/src/features/health/api.ts
git commit -m "feat(fhir): Frontend FHIR-API-Client"
```

---

## Task 8: Frontend — HealthSidebar + HealthPage

**Files:**
- Create: `frontend/src/features/health/HealthSidebar.tsx`
- Replace: `frontend/src/features/health/HealthPage.tsx`

- [ ] **Schritt 1: HealthSidebar anlegen**

```tsx
import { NavLink } from "react-router-dom"

interface SectionItem {
  to: string
  icon: string
  label: string
}

interface Section {
  title: string
  items: SectionItem[]
}

const SECTIONS: Section[] = [
  {
    title: "Patientenakte",
    items: [
      { to: "/health/uebersicht", icon: "🗂", label: "Übersicht" },
      { to: "/health/zeitstrahl", icon: "📅", label: "Zeitstrahl" },
    ],
  },
  {
    title: "Medizinisch",
    items: [
      { to: "/health/diagnosen",   icon: "🔴", label: "Diagnosen" },
      { to: "/health/medikamente", icon: "💊", label: "Medikamente" },
      { to: "/health/laborwerte",  icon: "🧪", label: "Laborwerte" },
      { to: "/health/allergien",   icon: "🤧", label: "Allergien" },
      { to: "/health/impfungen",   icon: "💉", label: "Impfungen" },
      { to: "/health/eingriffe",   icon: "🔪", label: "Eingriffe" },
    ],
  },
  {
    title: "Kontakte",
    items: [
      { to: "/health/arztbesuche", icon: "🏥", label: "Arztbesuche" },
      { to: "/health/befunde",     icon: "📋", label: "Befunde" },
      { to: "/health/dokumente",   icon: "📄", label: "Dokumente" },
    ],
  },
  {
    title: "Tracking",
    items: [
      { to: "/health/apple",  icon: "🍎", label: "Apple Health" },
      { to: "/health/schlaf", icon: "😴", label: "Schlaf" },
    ],
  },
  {
    title: "KI",
    items: [
      { to: "/health/ki", icon: "💬", label: "KI-Assistent" },
    ],
  },
]

export function HealthSidebar() {
  return (
    <nav className="w-48 flex-shrink-0 flex flex-col gap-4 py-2">
      {SECTIONS.map((section) => (
        <div key={section.title}>
          <p className="px-3 mb-1 text-[10px] font-bold uppercase tracking-widest text-zinc-600">
            {section.title}
          </p>
          {section.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  isActive
                    ? "bg-rose-500/10 text-rose-300 border-l-2 border-rose-500"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[4%] border-l-2 border-transparent"
                }`
              }
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      ))}
    </nav>
  )
}
```

- [ ] **Schritt 2: HealthPage ersetzen**

```tsx
import { Navigate, Route, Routes } from "react-router-dom"
import { Activity } from "lucide-react"
import { HealthSidebar } from "./HealthSidebar"
import { KiFloatingButton } from "./KiFloatingButton"
import { UebersichtView }   from "./views/UebersichtView"
import { ZeitstrahlView }   from "./views/ZeitstrahlView"
import { DiagnosenView }    from "./views/DiagnosenView"
import { MedikamenteView }  from "./views/MedikamenteView"
import { LaborwerteView }   from "./views/LaborwerteView"
import { SimpleListView }   from "./views/SimpleListView"
import { KiAssistentView }  from "./views/KiAssistentView"
import { TrendChart }       from "./_TrendChart"
import { SleepChart }       from "./_SleepChart"

export function HealthPage() {
  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
          <Activity size={18} className="text-rose-400" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">Gesundheit</h1>
          <p className="text-xs text-zinc-500">Digitale Patientenakte</p>
        </div>
      </div>

      <div className="flex gap-6">
        <HealthSidebar />
        <div className="flex-1 min-w-0 relative">
          <Routes>
            <Route index element={<Navigate to="uebersicht" replace />} />
            <Route path="uebersicht"   element={<UebersichtView />} />
            <Route path="zeitstrahl"   element={<ZeitstrahlView />} />
            <Route path="diagnosen"    element={<DiagnosenView />} />
            <Route path="medikamente"  element={<MedikamenteView />} />
            <Route path="laborwerte"   element={<LaborwerteView />} />
            <Route path="allergien"    element={<SimpleListView resourceType="AllergyIntolerance" title="Allergien" icon="🤧" />} />
            <Route path="impfungen"    element={<SimpleListView resourceType="Immunization" title="Impfungen" icon="💉" />} />
            <Route path="eingriffe"    element={<SimpleListView resourceType="Procedure" title="Eingriffe" icon="🔪" />} />
            <Route path="arztbesuche"  element={<SimpleListView resourceType="Encounter" title="Arztbesuche" icon="🏥" />} />
            <Route path="befunde"      element={<SimpleListView resourceType="DiagnosticReport" title="Befunde" icon="📋" />} />
            <Route path="dokumente"    element={<SimpleListView resourceType="DocumentReference" title="Dokumente" icon="📄" />} />
            <Route path="apple"        element={<AppleHealthWrapper />} />
            <Route path="schlaf"       element={<SchlafWrapper />} />
            <Route path="ki"           element={<KiAssistentView />} />
          </Routes>
          <KiFloatingButton />
        </div>
      </div>
    </div>
  )
}

function AppleHealthWrapper() {
  return <div className="space-y-4"><TrendChart summary={null} /></div>
}

function SchlafWrapper() {
  return <div className="space-y-4"><SleepChart summary={null} /></div>
}
```

- [ ] **Schritt 3: Commit**

```bash
git add frontend/src/features/health/HealthSidebar.tsx frontend/src/features/health/HealthPage.tsx
git commit -m "feat(fhir): HealthPage mit Aktenschrank-Sidebar"
```

---

## Task 9: Frontend — Shared Components

**Files:**
- Create: `frontend/src/features/health/components/ResourceTable.tsx`
- Create: `frontend/src/features/health/components/FhirImportButton.tsx`
- Create: `frontend/src/features/health/KiFloatingButton.tsx`

- [ ] **Schritt 1: ResourceTable**

```tsx
interface Column<T> {
  key: keyof T | string
  label: string
  render?: (row: T) => React.ReactNode
}

interface Props<T> {
  rows: T[]
  columns: Column<T>[]
  emptyText?: string
}

export function ResourceTable<T extends Record<string, unknown>>({ rows, columns, emptyText = "Keine Einträge" }: Props<T>) {
  if (rows.length === 0) {
    return <p className="text-sm text-zinc-500 py-8 text-center">{emptyText}</p>
  }
  return (
    <div className="rounded-xl border border-white/[6%] overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/[6%] bg-zinc-900/50">
            {columns.map((col) => (
              <th key={String(col.key)} className="px-4 py-2 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-white/[4%] hover:bg-white/[2%] transition-colors">
              {columns.map((col) => (
                <td key={String(col.key)} className="px-4 py-3 text-zinc-300">
                  {col.render ? col.render(row) : String(row[col.key as keyof T] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Schritt 2: FhirImportButton**

```tsx
import { useState, useRef } from "react"
import { Upload } from "lucide-react"
import { fhirApi } from "../api"

interface Props {
  onImported?: (result: { imported: number; updated: number }) => void
}

export function FhirImportButton({ onImported }: Props) {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setLoading(true)
    setMessage(null)
    try {
      const result = await fhirApi.importBundle(file)
      setMessage(`${result.imported} importiert, ${result.updated} aktualisiert`)
      onImported?.(result)
    } catch {
      setMessage("Fehler beim Import — ist das eine gültige FHIR-Datei?")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-3">
      <input
        ref={inputRef}
        type="file"
        accept=".json"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={loading}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-rose-500/10 text-rose-300 border border-rose-500/20 hover:bg-rose-500/20 transition-colors disabled:opacity-50"
      >
        <Upload size={14} />
        {loading ? "Importiere…" : "Akte aktualisieren"}
      </button>
      {message && <span className="text-xs text-zinc-400">{message}</span>}
    </div>
  )
}
```

- [ ] **Schritt 3: KiFloatingButton**

```tsx
import { MessageCircle } from "lucide-react"
import { useNavigate, useLocation } from "react-router-dom"

const ROUTE_TO_TYPES: Record<string, string> = {
  "/health/diagnosen":   "Condition",
  "/health/medikamente": "MedicationRequest",
  "/health/laborwerte":  "Observation",
  "/health/allergien":   "AllergyIntolerance",
  "/health/impfungen":   "Immunization",
  "/health/eingriffe":   "Procedure",
  "/health/arztbesuche": "Encounter",
  "/health/befunde":     "DiagnosticReport",
}

export function KiFloatingButton() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const resourceType = ROUTE_TO_TYPES[pathname]

  if (pathname === "/health/ki") return null

  const label = resourceType ? `KI zu ${resourceType} fragen` : "KI fragen"

  return (
    <button
      onClick={() => navigate("/health/ki", { state: { resourceType } })}
      className="fixed bottom-6 right-6 flex items-center gap-2 px-4 py-2.5 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium shadow-lg shadow-indigo-900/40 transition-all hover:scale-105"
    >
      <MessageCircle size={16} />
      {label}
    </button>
  )
}
```

- [ ] **Schritt 4: Commit**

```bash
git add frontend/src/features/health/components/ frontend/src/features/health/KiFloatingButton.tsx
git commit -m "feat(fhir): ResourceTable, FhirImportButton, KiFloatingButton"
```

---

## Task 10: Frontend — Hauptviews

**Files:**
- Create: `frontend/src/features/health/views/UebersichtView.tsx`
- Create: `frontend/src/features/health/views/ZeitstrahlView.tsx`
- Create: `frontend/src/features/health/views/DiagnosenView.tsx`
- Create: `frontend/src/features/health/views/MedikamenteView.tsx`
- Create: `frontend/src/features/health/views/LaborwerteView.tsx`
- Create: `frontend/src/features/health/views/SimpleListView.tsx`

- [ ] **Schritt 1: UebersichtView**

```tsx
import { useEffect, useState } from "react"
import { fhirApi, type FhirSummary } from "../api"
import { FhirImportButton } from "../components/FhirImportButton"

const CATEGORIES = [
  { type: "Condition", icon: "🔴", label: "Diagnosen" },
  { type: "MedicationRequest", icon: "💊", label: "Medikamente" },
  { type: "Observation", icon: "🧪", label: "Laborwerte" },
  { type: "AllergyIntolerance", icon: "🤧", label: "Allergien" },
  { type: "Immunization", icon: "💉", label: "Impfungen" },
  { type: "Encounter", icon: "🏥", label: "Arztbesuche" },
]

export function UebersichtView() {
  const [summary, setSummary] = useState<FhirSummary | null>(null)

  const load = () => fhirApi.getSummary().then(setSummary).catch(() => setSummary({}))

  useEffect(() => { load() }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-zinc-100">Übersicht</h2>
        <FhirImportButton onImported={load} />
      </div>

      {summary === null ? (
        <div className="grid grid-cols-3 gap-3">
          {CATEGORIES.map((c) => (
            <div key={c.type} className="h-20 rounded-xl bg-zinc-900/50 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {CATEGORIES.map((c) => (
            <div key={c.type} className="rounded-xl border border-white/[6%] bg-zinc-900/40 p-4">
              <div className="text-lg mb-1">{c.icon}</div>
              <div className="text-2xl font-bold text-zinc-100">{summary[c.type] ?? 0}</div>
              <div className="text-xs text-zinc-500 mt-0.5">{c.label}</div>
            </div>
          ))}
        </div>
      )}

      {summary && Object.keys(summary).length === 0 && (
        <div className="rounded-xl border border-dashed border-white/10 p-8 text-center">
          <p className="text-zinc-500 text-sm">Noch keine Patientendaten importiert.</p>
          <p className="text-zinc-600 text-xs mt-1">Exportiere deine Akte aus der TK-App und lade die JSON-Datei hoch.</p>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Schritt 2: ZeitstrahlView**

```tsx
import { useEffect, useState } from "react"
import { fhirApi, type FhirTimelineEntry } from "../api"

const TYPE_COLORS: Record<string, string> = {
  Condition: "bg-red-500",
  MedicationRequest: "bg-blue-500",
  Observation: "bg-green-500",
  Encounter: "bg-purple-500",
  Immunization: "bg-yellow-500",
}

function entryTitle(entry: FhirTimelineEntry): string {
  const r = entry.resource as Record<string, unknown>
  if (entry.resource_type === "Condition") {
    const code = r.code as Record<string, unknown>
    const codings = (code?.coding as {display?: string}[]) ?? []
    return codings[0]?.display ?? (code?.text as string) ?? "Diagnose"
  }
  if (entry.resource_type === "Observation") {
    const code = r.code as Record<string, unknown>
    return (code?.text as string) ?? "Laborwert"
  }
  return entry.label
}

export function ZeitstrahlView() {
  const [entries, setEntries] = useState<FhirTimelineEntry[] | null>(null)

  useEffect(() => {
    fhirApi.getTimeline().then((d) => setEntries(d.entries)).catch(() => setEntries([]))
  }, [])

  if (entries === null) return <div className="h-48 rounded-xl bg-zinc-900/50 animate-pulse" />
  if (entries.length === 0) return <p className="text-zinc-500 text-sm py-8 text-center">Noch keine Daten importiert.</p>

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">Zeitstrahl</h2>
      <div className="relative pl-6">
        <div className="absolute left-2 top-0 bottom-0 w-px bg-zinc-800" />
        {entries.map((entry, i) => (
          <div key={i} className="relative mb-4">
            <div className={`absolute -left-4 top-1.5 w-2 h-2 rounded-full ${TYPE_COLORS[entry.resource_type] ?? "bg-zinc-500"}`} />
            <div className="rounded-lg border border-white/[6%] bg-zinc-900/40 px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-200">{entryTitle(entry)}</span>
                <span className="text-xs text-zinc-600">{entry.imported_at.slice(0, 10)}</span>
              </div>
              <span className="text-xs text-zinc-500">{entry.label}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Schritt 3: DiagnosenView**

```tsx
import { useEffect, useState } from "react"
import { fhirApi } from "../api"
import { ResourceTable } from "../components/ResourceTable"

interface DiagnoseRow {
  id: string
  name: string
  icd: string
  seit: string
  status: string
}

function parseCondition(r: Record<string, unknown>): DiagnoseRow {
  const code = r.code as Record<string, unknown>
  const codings = (code?.coding as {code?: string; display?: string}[]) ?? []
  const status = (r.clinicalStatus as Record<string, {code?: string}[]>)?.coding?.[0]?.code ?? ""
  const onset = (r.onsetDateTime ?? r.onsetString ?? "") as string
  return {
    id: r.id as string,
    name: codings[0]?.display ?? (code?.text as string) ?? "Unbekannt",
    icd: codings[0]?.code ?? "",
    seit: onset.slice(0, 10),
    status,
  }
}

export function DiagnosenView() {
  const [rows, setRows] = useState<DiagnoseRow[] | null>(null)

  useEffect(() => {
    fhirApi.getResources("Condition")
      .then((d) => setRows(d.resources.map((r) => parseCondition(r.resource as Record<string, unknown>))))
      .catch(() => setRows([]))
  }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">🔴 Diagnosen</h2>
      {rows === null ? <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" /> : (
        <ResourceTable
          rows={rows}
          columns={[
            { key: "name", label: "Diagnose" },
            { key: "icd", label: "ICD" },
            { key: "seit", label: "Seit" },
            {
              key: "status", label: "Status",
              render: (r) => (
                <span className={`text-xs px-2 py-0.5 rounded-full ${r.status === "active" ? "bg-red-950 text-red-400" : "bg-zinc-800 text-zinc-400"}`}>
                  {r.status === "active" ? "aktiv" : r.status === "resolved" ? "abgeklungen" : r.status}
                </span>
              ),
            },
          ]}
          emptyText="Keine Diagnosen importiert"
        />
      )}
    </div>
  )
}
```

- [ ] **Schritt 4: MedikamenteView**

```tsx
import { useEffect, useState } from "react"
import { fhirApi } from "../api"
import { ResourceTable } from "../components/ResourceTable"

interface MedRow { id: string; name: string; status: string; datum: string }

function parseMed(r: Record<string, unknown>): MedRow {
  const med = (r.medicationCodeableConcept ?? r.medicationReference ?? {}) as Record<string, unknown>
  const name = (med.text ?? med.display ?? "Unbekannt") as string
  return {
    id: r.id as string,
    name,
    status: (r.status ?? "") as string,
    datum: ((r.authoredOn ?? r.dateAsserted ?? "") as string).slice(0, 10),
  }
}

export function MedikamenteView() {
  const [rows, setRows] = useState<MedRow[] | null>(null)

  useEffect(() => {
    Promise.all([
      fhirApi.getResources("MedicationRequest"),
      fhirApi.getResources("MedicationStatement"),
    ]).then(([a, b]) => {
      const all = [...a.resources, ...b.resources].map((r) => parseMed(r.resource as Record<string, unknown>))
      setRows(all)
    }).catch(() => setRows([]))
  }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">💊 Medikamente</h2>
      {rows === null ? <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" /> : (
        <ResourceTable
          rows={rows}
          columns={[
            { key: "name", label: "Medikament" },
            { key: "status", label: "Status" },
            { key: "datum", label: "Datum" },
          ]}
          emptyText="Keine Medikamente importiert"
        />
      )}
    </div>
  )
}
```

- [ ] **Schritt 5: LaborwerteView**

```tsx
import { useEffect, useState } from "react"
import { fhirApi } from "../api"
import { ResourceTable } from "../components/ResourceTable"

interface LabRow { id: string; name: string; wert: string; datum: string }

function parseLab(r: Record<string, unknown>): LabRow {
  const code = r.code as Record<string, unknown>
  const name = (code?.text ?? (code?.coding as {display?: string}[])?.[0]?.display ?? "") as string
  const vq = r.valueQuantity as Record<string, unknown> | undefined
  const wert = vq ? `${vq.value} ${vq.unit ?? ""}`.trim() : (r.valueString ?? "") as string
  return {
    id: r.id as string,
    name,
    wert,
    datum: ((r.effectiveDateTime ?? "") as string).slice(0, 10),
  }
}

export function LaborwerteView() {
  const [rows, setRows] = useState<LabRow[] | null>(null)

  useEffect(() => {
    fhirApi.getResources("Observation")
      .then((d) => setRows(d.resources.map((r) => parseLab(r.resource as Record<string, unknown>))))
      .catch(() => setRows([]))
  }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">🧪 Laborwerte</h2>
      {rows === null ? <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" /> : (
        <ResourceTable
          rows={rows}
          columns={[
            { key: "name", label: "Parameter" },
            { key: "wert", label: "Wert" },
            { key: "datum", label: "Datum" },
          ]}
          emptyText="Keine Laborwerte importiert"
        />
      )}
    </div>
  )
}
```

- [ ] **Schritt 6: SimpleListView (generisch für alle restlichen Kategorien)**

```tsx
import { useEffect, useState } from "react"
import { fhirApi } from "../api"

interface Props {
  resourceType: string
  title: string
  icon: string
}

function summarize(r: Record<string, unknown>): string {
  // Versucht einen lesbaren Titel aus dem FHIR-Objekt zu extrahieren
  const tryPaths = [
    () => (r.code as Record<string, unknown>)?.text as string,
    () => ((r.code as Record<string, unknown>)?.coding as {display?: string}[])?.[0]?.display,
    () => (r.vaccineCode as Record<string, unknown>)?.text as string,
    () => (r.class as Record<string, unknown>)?.display as string,
    () => (r.type as {text?: string}[])?.[0]?.text,
    () => r.id as string,
  ]
  for (const fn of tryPaths) {
    try { const v = fn(); if (v) return v } catch {}
  }
  return JSON.stringify(r).slice(0, 80)
}

export function SimpleListView({ resourceType, title, icon }: Props) {
  const [items, setItems] = useState<string[] | null>(null)

  useEffect(() => {
    fhirApi.getResources(resourceType)
      .then((d) => setItems(d.resources.map((r) => summarize(r.resource as Record<string, unknown>))))
      .catch(() => setItems([]))
  }, [resourceType])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">{icon} {title}</h2>
      {items === null ? (
        <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" />
      ) : items.length === 0 ? (
        <p className="text-zinc-500 text-sm py-8 text-center">Keine {title} importiert.</p>
      ) : (
        <div className="rounded-xl border border-white/[6%] overflow-hidden">
          {items.map((item, i) => (
            <div key={i} className="px-4 py-3 border-b border-white/[4%] last:border-0 text-sm text-zinc-300 hover:bg-white/[2%]">
              {item}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Schritt 7: Commit**

```bash
git add frontend/src/features/health/views/
git commit -m "feat(fhir): alle Kategorie-Views — Übersicht, Zeitstrahl, Diagnosen, Medikamente, Labor, SimpleList"
```

---

## Task 11: Frontend — KI-Assistent View

**Files:**
- Create: `frontend/src/features/health/views/KiAssistentView.tsx`

- [ ] **Schritt 1: View anlegen**

```tsx
import { useState, useRef, useEffect } from "react"
import { useLocation } from "react-router-dom"
import { Send } from "lucide-react"

interface Message {
  role: "user" | "assistant"
  text: string
}

const SUGGESTIONS: Record<string, string[]> = {
  Condition: ["Erkläre meine Diagnosen", "Welche Diagnosen sind aktiv?", "Was bedeutet ICD I10?"],
  Observation: ["Wie hat sich mein HbA1c entwickelt?", "Zeige meine letzten Laborwerte"],
  MedicationRequest: ["Welche Medikamente nehme ich?", "Wann wurden meine Medikamente verschrieben?"],
  default: [
    "Welche Diagnosen habe ich?",
    "Was sind meine aktuellen Medikamente?",
    "Wie haben sich meine Laborwerte entwickelt?",
    "Wann war mein letzter Arztbesuch?",
  ],
}

async function askFhirKi(question: string, resourceType?: string): Promise<string> {
  const body: Record<string, unknown> = { message: question }
  if (resourceType) body.context_resource_type = resourceType
  const res = await fetch("/api/buddy/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("hh_token") ?? ""}`,
    },
    body: JSON.stringify({ ...body, tool_hints: ["query_fhir_data"] }),
  })
  if (!res.ok) throw new Error("Antwort fehlgeschlagen")
  const data = await res.json()
  return data.response ?? data.message ?? "Keine Antwort"
}

export function KiAssistentView() {
  const location = useLocation()
  const contextType = (location.state as {resourceType?: string})?.resourceType
  const suggestions = SUGGESTIONS[contextType ?? "default"] ?? SUGGESTIONS.default

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const send = async (text: string) => {
    if (!text.trim() || loading) return
    setMessages((prev) => [...prev, { role: "user", text }])
    setInput("")
    setLoading(true)
    try {
      const reply = await askFhirKi(text, contextType)
      setMessages((prev) => [...prev, { role: "assistant", text: reply }])
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "Fehler bei der Antwort. Bitte erneut versuchen." }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)]">
      <h2 className="text-base font-semibold text-zinc-100 mb-4">
        💬 KI-Assistent{contextType ? ` — ${contextType}` : ""}
      </h2>

      {messages.length === 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="px-3 py-1.5 text-xs rounded-lg bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
              m.role === "user"
                ? "bg-indigo-600/20 text-indigo-200 border border-indigo-500/20"
                : "bg-zinc-800/60 text-zinc-200 border border-white/[6%]"
            }`}>
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-zinc-800/60 border border-white/[6%] rounded-xl px-4 py-2.5">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); send(input) }}
        className="mt-3 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Stelle eine Frage zu deiner Patientenakte…"
          className="flex-1 bg-zinc-900 border border-white/[8%] rounded-xl px-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500/40"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 transition-colors"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  )
}
```

- [ ] **Schritt 2: Commit**

```bash
git add frontend/src/features/health/views/KiAssistentView.tsx
git commit -m "feat(fhir): KI-Assistent View mit Kontext-Suggestions"
```

---

## Task 12: Frontend bauen + testen

- [ ] **Schritt 1: TypeScript-Check**

```bash
cd /home/till/claudeneu/frontend
npx tsc --noEmit 2>&1 | head -30
```

Fehler beheben bis keine Fehler mehr.

- [ ] **Schritt 2: Build**

```bash
cd /home/till/claudeneu/frontend
npm run build 2>&1 | tail -10
```

Erwartete Ausgabe: Build abgeschlossen ohne Fehler.

- [ ] **Schritt 3: Final Commit**

```bash
git add -A
git commit -m "feat(fhir): Digitale Patientenakte — vollständig implementiert"
git push origin main
```

---

## Selbst-Review (Spec-Abgleich)

| Spec-Anforderung | Abgedeckt in |
|---|---|
| FHIR Bundle Import + Merge | Task 2 (db/fhir.py), Task 3 (API), Task 4 (Tests) |
| user_id Isolation | Task 2 (UNIQUE idx), Task 3 (require_auth), Task 4 (Isolationstest) |
| Aktenschrank-Sidebar | Task 8 (HealthSidebar) |
| Zeitstrahl | Task 10 (ZeitstrahlView) |
| Alle 10 Kategorien | Task 10 (Views) + Task 8 (Routes) |
| KI-Tool query_fhir_data | Task 5 |
| KI-Assistent Tab | Task 11 |
| Floating KI-Button | Task 9 |
| FhirImportButton | Task 9 |
| Apple Health + Schlaf erhalten | Task 8 (Wrapper-Routes) |
| Fehler bei ungültigem Bundle | Task 3 (HTTP 422), Task 4 (Test) |
| Leere Kategorie = "Keine Einträge" | Task 10 (alle Views) |
| FHIR-JSON nicht in Logs | Task 3 (logger loggt nur Zähler) |
