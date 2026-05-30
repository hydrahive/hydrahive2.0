# Patientenakte (ePA-light) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine strukturierte, durchsuchbare, persistente **Multi-Patient-Akte** in der Health-Extension, die per Token-REST-API von Agenten befüllt wird, mit UI (Dashboard/Timeline/Detail-Listen/Lab-Charts), Dokumenten + Volltextsuche und DSGVO-Funktionen (Audit, Verschlüsselung, Export, Löschung).

**Architecture:** Eigene relationale Domäne `patientenakte/` (NICHT auf dem bestehenden FHIR-Blob-Store `db/fhir.py` aufbauend — der ist single-patient, blob-only, ohne `quelle/confidence/verifiziert/external_id` und ohne echte Felder). Pro Entität eine getypte Tabelle mit gemeinsamen Spalten + entity-spezifischen Spalten; ein **Registry-getriebener generischer Service-/Route-Layer** vermeidet 9× CRUD-Duplikat (DRY, CLAUDE.md). Die bestehende read-only eGA/FHIR-Schicht bleibt unangetastet und wird im UI unter eine eigene Sektion „Kassendaten / Import" umgruppiert; die neue Akte wird die primäre „Patientenakte" (Tills Entscheidung).

**Tech Stack:** Python 3.12 + FastAPI, SQLite (numbered migrations `db/migrations/NNN_*.sql`), React + TS + Vite, SQLite FTS5 (Phase 3), AES-GCM via `credentials/_crypto.py` (Phase 4). Auth: `require_auth` (JWT) + `hhk_`-API-Keys (Agent-Befüllung) aus `api/middleware/auth.py`.

---

## Entscheidungen (Stand 2026-05-30, mit Till abgestimmt)

1. **Wer baut:** Joshua, im Core-Repo `hydrahive2.0`, TDD → Review → security-audit → Deploy auf `.22`.
2. **Koexistenz:** Neue schreibbare Akte = primäre „Patientenakte". Bestehende read-only Views (Übersicht/Zeitstrahl/Diagnosen/Medikamente/Labor/Allergien/Impfungen/Eingriffe/Arztbesuche/Abrechnung/Krankenhaus/Befunde/Dokumente) → Sidebar-Sektion „Kassendaten / Import (eGA/FHIR)". Keine Logik der alten Views wird geändert, nur Gruppierung/Routing.
3. **DB:** Eigene SQLite-Tabellen (Core-Muster), Migration `023_patientenakte.sql`.
4. **Schema-Quelle:** SQL-Migration ist Single Source of Truth für DDL. Python-Registry (`schema.py`) bildet API↔Spalten ab; ein **Guard-Test** (PRAGMA table_info) erzwingt Konsistenz, damit nichts driftet.
5. **OCR:** Agent liefert `ocr_text` mit (Lastenheft §3.3 / Prompt §5). Keine server-seitige OCR-Engine in v1.

### Offene Entscheidung für Phase 4 (jetzt NICHT vorwegnehmen — security-audit)
**Verschlüsselung-at-rest vs. Volltextsuche/Filter sind in Konflikt:** Eine verschlüsselte Spalte ist nicht mehr `LIKE`/FTS-durchsuchbar oder filterbar. Optionen, in Phase 4 mit Till + security-audit zu entscheiden:
- (a) Nur höchstsensible Felder spaltenweise verschlüsseln (Patientenname, Versicherungsnummern, Dokument-Dateien on disk), klinische Felder bleiben query-bar, geschützt durch Datei-Rechte (0600) + Full-Disk-Encryption + App-Zugriffskontrolle + Audit.
- (b) Ganze DB via SQLCipher (neue Dependency, Code nutzt heute plain `sqlite3`).
- (c) FTS-Index nur über nicht-verschlüsselte Felder; sensible Freitexte verschlüsselt + nicht durchsuchbar.
→ Default-Empfehlung (a). Final in Phase 4.

---

## SPEC-Gate (VOR Phase 1 — CLAUDE.md Regel 4 + 8)

Die Patientenakte steht nicht in `SPEC.md`. Bevor Code geschrieben wird:
1. SPEC-Sektion „Patientenakte (Health-Extension)" entwerfen (Vorschlag unten in Anhang A).
2. Tills explizites OK abwarten.
3. **Standalone-Commit** (nur `SPEC.md`, kein Code daneben — Pre-Commit-Hook erzwingt das).

Erst danach Task 1.

---

## Datenmodell (grounded am realen YAML-Prototyp `akten/alex/`)

**Gemeinsame Spalten jeder Entitäts-Tabelle:**
```
id TEXT PRIMARY KEY,          -- uuid7()
patient_id TEXT NOT NULL,     -- FK akte_patient(id) ON DELETE CASCADE
external_id TEXT,             -- Idempotenz: UNIQUE(patient_id, external_id) wo gesetzt
quelle TEXT,
confidence REAL,
verifiziert INTEGER NOT NULL DEFAULT 0,
sort_date TEXT,               -- best-effort ISO (YYYY-MM-DD) für Timeline; nullable
extra_json TEXT,              -- Arrays/seltene Felder als JSON
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL
```

**`akte_patient`:** `id, owner_user_id, slug, name, vorname, geburtsdatum, geburtsort, geschlecht, blutgruppe, rh_faktor, adresse_json, telefon_json, email, notfallkontakt_json, versicherung_json, beruf, arbeitgeber, external_id, created_at, updated_at`

**Entitäts-Tabellen (typed columns zusätzlich zu den gemeinsamen):**

| key (API) | table | typed columns | date→sort_date | extra_json |
|---|---|---|---|---|
| `conditions` | `akte_condition` | diagnose, icd_code, status, diagnostiziert_am, arzt, koerperstelle, erstmanifestation, bemerkungen | diagnostiziert_am | — |
| `medications` | `akte_medication` | name, wirkstoff, atc_code, klasse, dosierung, beginn, ende, arzt, zweck, status, letzte_verordnung | beginn | nebenwirkungen[] |
| `observations` | `akte_observation` | parameter, wert (REAL), wert_text, einheit, referenz_min (REAL), referenz_max (REAL), flag, datum, labor, material | datum | — |
| `events` | `akte_encounter` | datum_von, datum_bis, typ, einrichtung, fachabteilung, fallnummer, hauptdiagnose, verlauf | datum_von | nebendiagnosen[], prozeduren[], op_codes[], entlassmedikation[] |
| `imaging` | `akte_imaging` | datum, modalitaet, region, einrichtung, ueberweiser, serien_beschreibung, anzahl_bilder, dicom_pfad, befund | datum | vorschau_bilder[] |
| `allergies` | `akte_allergy` | substanz, reaktion, schweregrad, festgestellt_am | festgestellt_am | — |
| `practitioners` | `akte_practitioner` | name, fach, einrichtung, adresse, telefon, rolle | — | — |
| `documents` | `akte_document` | titel, typ, datum, datei_pfad, mime_type, ocr_text | datum | verknuepfte_entitaeten[] |
| `notes` | `akte_note` | titel, inhalt, kategorie, datum | datum | — |

> `wert REAL` + `wert_text TEXT`: Laborwerte sind meist numerisch (Trend-Charts), gelegentlich Text („negativ"). Numerisch → `wert`, sonst `wert_text`.

---

## Phasen-Übersicht

| Phase | Inhalt | Liefert (testbar) |
|---|---|---|
| **1 Fundament** | Schema + Service + Token-REST-API + Prototyp-Migration | Agent kann Akte befüllen, Daten persistieren, abfragen |
| **2 UI** | Patienten-Picker + Dashboard + Timeline + Detail-Listen + Lab-Charts + Sidebar-Restructure | Till sieht die Akte im Browser |
| **3 Dokumente** | Upload + ocr_text speichern + FTS5-Volltextsuche | Dokumente hochladen, Volltext finden |
| **4 DSGVO** | Audit-Log + Verschlüsselung-at-rest + Export + Löschung + security-audit | Compliance-Funktionen |

**CLAUDE.md Regel 2:** Jede Phase komplett fertig (gebaut, von Till getestet, deployed), dann die nächste. **Phase 1 ist unten voll als bite-sized Tasks ausgearbeitet. Phasen 2–4 sind als Roadmap gescoped und werden je zu Phasenbeginn via `writing-plans` zum detaillierten Plan ausgearbeitet** — bewusst, weil ihre konkrete Form von den realen Shapes aus Phase 1 abhängt.

---

# PHASE 1 — Fundament

**Files (Phase 1):**
- Create: `core/src/hydrahive/db/migrations/023_patientenakte.sql`
- Create: `core/src/hydrahive/patientenakte/__init__.py`
- Create: `core/src/hydrahive/patientenakte/schema.py` (Registry + EntitySpec)
- Create: `core/src/hydrahive/patientenakte/models.py` (Patient/EntityRecord TypedDicts)
- Create: `core/src/hydrahive/patientenakte/_dates.py` (best-effort sort_date Parser)
- Create: `core/src/hydrahive/patientenakte/patients.py` (Patient-CRUD)
- Create: `core/src/hydrahive/patientenakte/entities.py` (generischer Entity-CRUD + Batch + Upsert)
- Create: `core/src/hydrahive/patientenakte/views.py` (timeline + summary)
- Create: `core/src/hydrahive/api/routes/patientenakte.py` (REST)
- Modify: `core/src/hydrahive/api/main.py` (Router registrieren)
- Create: `core/src/hydrahive/skills/system_defaults/medical-akte.md` (Befüll-Anleitung für Agenten)
- Create: `core/scripts/import_akte_prototype.py` (YAML/CSV-Migration)
- Test: `core/tests/test_akte_schema.py`, `test_akte_patients.py`, `test_akte_entities.py`, `test_akte_views.py`, `test_akte_api.py`, `test_akte_import.py`

---

### Task 1: Migration 023 — Schema

**Files:**
- Create: `core/src/hydrahive/db/migrations/023_patientenakte.sql`
- Test: `core/tests/test_akte_schema.py`

- [ ] **Step 1: Write the failing test** (`test_akte_schema.py`)

```python
import sqlite3
from hydrahive.db.connection import db

EXPECTED_TABLES = {
    "akte_patient", "akte_condition", "akte_medication", "akte_observation",
    "akte_encounter", "akte_imaging", "akte_allergy", "akte_practitioner",
    "akte_document", "akte_note",
}

def test_migration_creates_all_akte_tables():
    with db() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'akte_%'"
        ).fetchall()
    names = {r["name"] for r in rows}
    assert EXPECTED_TABLES <= names

def test_observation_has_numeric_wert_and_refs():
    with db() as conn:
        cols = {r["name"]: r["type"] for r in conn.execute("PRAGMA table_info(akte_observation)")}
    assert cols.get("wert") == "REAL"
    assert cols.get("referenz_min") == "REAL"
    assert "wert_text" in cols

def test_entity_has_common_columns():
    with db() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(akte_condition)")}
    assert {"id","patient_id","external_id","quelle","confidence","verifiziert",
            "sort_date","extra_json","created_at","updated_at"} <= cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_schema.py -v`
Expected: FAIL (tables don't exist).

- [ ] **Step 3: Write the migration**

Write `023_patientenakte.sql` with `akte_patient` + 9 entity tables. Pattern (gemeinsame Spalten in jeder Entität, `external_id` UNIQUE pro patient, `ON DELETE CASCADE`, Index auf `(patient_id, sort_date)`):

```sql
CREATE TABLE akte_patient (
  id TEXT PRIMARY KEY,
  owner_user_id TEXT NOT NULL,
  slug TEXT,
  name TEXT, vorname TEXT, geburtsdatum TEXT, geburtsort TEXT,
  geschlecht TEXT, blutgruppe TEXT, rh_faktor TEXT,
  adresse_json TEXT, telefon_json TEXT, email TEXT,
  notfallkontakt_json TEXT, versicherung_json TEXT,
  beruf TEXT, arbeitgeber TEXT, external_id TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX idx_akte_patient_owner ON akte_patient(owner_user_id);

-- Beispiel Entität (gleiches Muster für alle 9, nur typed columns variieren):
CREATE TABLE akte_condition (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL REFERENCES akte_patient(id) ON DELETE CASCADE,
  external_id TEXT, quelle TEXT, confidence REAL,
  verifiziert INTEGER NOT NULL DEFAULT 0,
  sort_date TEXT, extra_json TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  diagnose TEXT, icd_code TEXT, status TEXT, diagnostiziert_am TEXT,
  arzt TEXT, koerperstelle TEXT, erstmanifestation TEXT, bemerkungen TEXT
);
CREATE INDEX idx_akte_condition_patient ON akte_condition(patient_id, sort_date);
CREATE UNIQUE INDEX idx_akte_condition_extid
  ON akte_condition(patient_id, external_id) WHERE external_id IS NOT NULL;
-- ... akte_medication, akte_observation (mit wert REAL, wert_text, referenz_min/max REAL),
--     akte_encounter, akte_imaging, akte_allergy, akte_practitioner, akte_document, akte_note
--     je nach Spalten-Tabelle oben. PRAGMA foreign_keys ist in connection.py zu prüfen (s. Step 4).
```

Vollständige typed columns je Tabelle siehe Datenmodell-Tabelle oben.

- [ ] **Step 4: Cascade-Delete sicherstellen**

`db/connection.py` lesen: ist `PRAGMA foreign_keys=ON` gesetzt? Falls nicht, kaskadiert `ON DELETE CASCADE` nicht. Wenn nicht gesetzt → in Task 3 (`delete_patient`) explizit alle Entitäts-Tabellen löschen statt auf Kaskade zu vertrauen. (Verifizieren, nicht annehmen.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_schema.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/src/hydrahive/db/migrations/023_patientenakte.sql core/tests/test_akte_schema.py
git commit -m "feat(akte): add patientenakte DB schema (migration 023)"
```

---

### Task 2: Registry + Models + Konsistenz-Guard

**Files:**
- Create: `core/src/hydrahive/patientenakte/schema.py`
- Create: `core/src/hydrahive/patientenakte/models.py`
- Create: `core/src/hydrahive/patientenakte/__init__.py`
- Test: `core/tests/test_akte_schema.py` (erweitern)

- [ ] **Step 1: Write the failing test** (an `test_akte_schema.py` anhängen)

```python
from hydrahive.patientenakte.schema import ENTITIES
from hydrahive.db.connection import db

def test_registry_columns_subset_of_tables():
    """Guard: jede Registry-Spalte existiert wirklich in der Tabelle (kein Drift)."""
    with db() as conn:
        for spec in ENTITIES.values():
            actual = {r["name"] for r in conn.execute(f"PRAGMA table_info({spec.table})")}
            declared = set(spec.fields)
            missing = declared - actual
            assert not missing, f"{spec.table}: registry fields not in table: {missing}"

def test_registry_keys_match_lastenheft():
    assert set(ENTITIES) == {
        "conditions","medications","observations","events","imaging",
        "allergies","practitioners","documents","notes",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_schema.py::test_registry_columns_subset_of_tables -v`
Expected: FAIL (ImportError: ENTITIES).

- [ ] **Step 3: Write `schema.py`**

```python
"""Registry der Patientenakte-Entitäten — bildet API-Felder auf SQL-Spalten ab."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EntitySpec:
    key: str                         # API-Pfadsegment, z.B. "conditions"
    table: str                       # SQL-Tabelle, z.B. "akte_condition"
    label: str                       # UI-Label
    fields: tuple[str, ...]          # getypte Spalten (API akzeptiert/liefert)
    date_field: str | None = None    # speist sort_date
    array_fields: tuple[str, ...] = ()  # -> extra_json
    numeric_fields: tuple[str, ...] = ()  # in REST als Zahl casten


COMMON_FIELDS = ("external_id", "quelle", "confidence", "verifiziert")

ENTITIES: dict[str, EntitySpec] = {
    "conditions": EntitySpec(
        "conditions", "akte_condition", "Diagnosen",
        ("diagnose","icd_code","status","diagnostiziert_am","arzt",
         "koerperstelle","erstmanifestation","bemerkungen"),
        date_field="diagnostiziert_am"),
    "medications": EntitySpec(
        "medications", "akte_medication", "Medikamente",
        ("name","wirkstoff","atc_code","klasse","dosierung","beginn","ende",
         "arzt","zweck","status","letzte_verordnung"),
        date_field="beginn", array_fields=("nebenwirkungen",)),
    "observations": EntitySpec(
        "observations", "akte_observation", "Laborwerte",
        ("parameter","wert","wert_text","einheit","referenz_min","referenz_max",
         "flag","datum","labor","material"),
        date_field="datum", numeric_fields=("wert","referenz_min","referenz_max")),
    "events": EntitySpec(
        "events", "akte_encounter", "Ereignisse",
        ("datum_von","datum_bis","typ","einrichtung","fachabteilung","fallnummer",
         "hauptdiagnose","verlauf"),
        date_field="datum_von",
        array_fields=("nebendiagnosen","prozeduren","op_codes","entlassmedikation")),
    "imaging": EntitySpec(
        "imaging", "akte_imaging", "Bildgebung",
        ("datum","modalitaet","region","einrichtung","ueberweiser",
         "serien_beschreibung","anzahl_bilder","dicom_pfad","befund"),
        date_field="datum", array_fields=("vorschau_bilder",)),
    "allergies": EntitySpec(
        "allergies", "akte_allergy", "Allergien",
        ("substanz","reaktion","schweregrad","festgestellt_am"),
        date_field="festgestellt_am"),
    "practitioners": EntitySpec(
        "practitioners", "akte_practitioner", "Ärzte",
        ("name","fach","einrichtung","adresse","telefon","rolle")),
    "documents": EntitySpec(
        "documents", "akte_document", "Dokumente",
        ("titel","typ","datum","datei_pfad","mime_type","ocr_text"),
        date_field="datum", array_fields=("verknuepfte_entitaeten",)),
    "notes": EntitySpec(
        "notes", "akte_note", "Notizen",
        ("titel","inhalt","kategorie","datum"),
        date_field="datum"),
}
```

- [ ] **Step 4: Write `models.py`** (TypedDicts für IDE/Validierung)

```python
"""Typen der Patientenakte."""
from __future__ import annotations

from typing import Any, TypedDict


class Patient(TypedDict, total=False):
    id: str
    owner_user_id: str
    slug: str
    name: str
    vorname: str
    geburtsdatum: str
    geschlecht: str
    adresse: dict[str, Any]
    versicherung: dict[str, Any]
    notfallkontakt: dict[str, Any]
    external_id: str
    created_at: str
    updated_at: str
```

`__init__.py`: re-export `ENTITIES`, `EntitySpec`.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_schema.py -v`
Expected: PASS (Guard greift jetzt — bestätigt Registry↔SQL-Konsistenz).

- [ ] **Step 6: Commit**

```bash
git add core/src/hydrahive/patientenakte/ core/tests/test_akte_schema.py
git commit -m "feat(akte): entity registry + schema consistency guard"
```

---

### Task 3: Patient-CRUD

**Files:**
- Create: `core/src/hydrahive/patientenakte/patients.py`
- Create: `core/src/hydrahive/patientenakte/_dates.py`
- Test: `core/tests/test_akte_patients.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from hydrahive.patientenakte import patients

def test_create_and_get_patient():
    pid = patients.create("u1", {"slug": "alex", "name": "Molke", "vorname": "Alexander",
                                 "adresse": {"ort": "Frankfurt"}})
    p = patients.get("u1", pid)
    assert p["name"] == "Molke"
    assert p["adresse"]["ort"] == "Frankfurt"   # JSON-Roundtrip

def test_list_only_own_patients():
    patients.create("u1", {"slug": "a"})
    patients.create("u2", {"slug": "b"})
    assert {p["slug"] for p in patients.list_for("u1")} == {"a"}

def test_get_foreign_patient_returns_none():
    pid = patients.create("u1", {"slug": "a"})
    assert patients.get("u2", pid) is None

def test_delete_cascades_entities():
    from hydrahive.patientenakte import entities
    pid = patients.create("u1", {"slug": "a"})
    entities.create("u1", pid, "conditions", {"diagnose": "X"})
    patients.delete("u1", pid)
    assert patients.get("u1", pid) is None
    assert entities.list_for("u1", pid, "conditions") == []  # via fresh patient check
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_patients.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write `_dates.py`** (best-effort ISO-Extraktion)

```python
"""Best-effort sort_date: erstes YYYY-MM-DD / YYYY-MM / YYYY aus Freitext."""
from __future__ import annotations

import re

_ISO = re.compile(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?")


def to_sort_date(value: str | None) -> str | None:
    if not value:
        return None
    m = _ISO.search(value)
    if not m:
        return None
    y, mo, d = m.group(1), m.group(2) or "01", m.group(3) or "01"
    return f"{y}-{mo}-{d}"
```

- [ ] **Step 4: Write `patients.py`**

```python
"""Patient-Stammdaten — CRUD mit Owner-Isolation."""
from __future__ import annotations

import json
from typing import Any

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db

_JSON_FIELDS = {"adresse": "adresse_json", "telefon": "telefon_json",
                "notfallkontakt": "notfallkontakt_json", "versicherung": "versicherung_json"}
_SCALAR = ("slug","name","vorname","geburtsdatum","geburtsort","geschlecht",
           "blutgruppe","rh_faktor","email","beruf","arbeitgeber","external_id")


def create(user_id: str, data: dict[str, Any]) -> str:
    pid = uuid7()
    ts = now_iso()
    cols = ["id","owner_user_id","created_at","updated_at"]
    vals: list[Any] = [pid, user_id, ts, ts]
    for f in _SCALAR:
        if f in data:
            cols.append(f); vals.append(data[f])
    for f, col in _JSON_FIELDS.items():
        if f in data:
            cols.append(col); vals.append(json.dumps(data[f]))
    ph = ",".join("?" * len(cols))
    with db() as conn:
        conn.execute(f"INSERT INTO akte_patient ({','.join(cols)}) VALUES ({ph})", vals)
    return pid


def _row_to_patient(row) -> dict[str, Any]:
    out = {k: row[k] for k in row.keys() if not k.endswith("_json")}
    for f, col in _JSON_FIELDS.items():
        if row[col]:
            out[f] = json.loads(row[col])
    return out


def get(user_id: str, pid: str) -> dict[str, Any] | None:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM akte_patient WHERE id=? AND owner_user_id=?", (pid, user_id)
        ).fetchone()
    return _row_to_patient(row) if row else None


def list_for(user_id: str) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM akte_patient WHERE owner_user_id=? ORDER BY slug", (user_id,)
        ).fetchall()
    return [_row_to_patient(r) for r in rows]


def update(user_id: str, pid: str, data: dict[str, Any]) -> bool:
    sets, vals = ["updated_at=?"], [now_iso()]
    for f in _SCALAR:
        if f in data:
            sets.append(f"{f}=?"); vals.append(data[f])
    for f, col in _JSON_FIELDS.items():
        if f in data:
            sets.append(f"{col}=?"); vals.append(json.dumps(data[f]))
    vals += [pid, user_id]
    with db() as conn:
        cur = conn.execute(
            f"UPDATE akte_patient SET {','.join(sets)} WHERE id=? AND owner_user_id=?", vals)
    return cur.rowcount > 0


def delete(user_id: str, pid: str) -> bool:
    # Falls PRAGMA foreign_keys nicht aktiv ist (Task 1 Step 4): hier entity-Tabellen explizit leeren.
    with db() as conn:
        cur = conn.execute(
            "DELETE FROM akte_patient WHERE id=? AND owner_user_id=?", (pid, user_id))
    return cur.rowcount > 0
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_patients.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/src/hydrahive/patientenakte/patients.py core/src/hydrahive/patientenakte/_dates.py core/tests/test_akte_patients.py
git commit -m "feat(akte): patient CRUD with owner isolation"
```

---

### Task 4: Generischer Entity-CRUD + Batch + Idempotenz

**Files:**
- Create: `core/src/hydrahive/patientenakte/entities.py`
- Test: `core/tests/test_akte_entities.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from hydrahive.patientenakte import patients, entities

@pytest.fixture
def pid():
    return patients.create("u1", {"slug": "alex"})

def test_create_and_list(pid):
    eid = entities.create("u1", pid, "conditions",
                          {"diagnose": "Diabetes", "icd_code": "E11", "diagnostiziert_am": "2021-05-01"})
    items = entities.list_for("u1", pid, "conditions")
    assert len(items) == 1
    assert items[0]["diagnose"] == "Diabetes"
    assert items[0]["sort_date"] == "2021-05-01"   # aus diagnostiziert_am abgeleitet

def test_external_id_upsert_no_duplicate(pid):
    entities.create("u1", pid, "conditions", {"external_id": "x1", "diagnose": "A"})
    entities.create("u1", pid, "conditions", {"external_id": "x1", "diagnose": "A-korrigiert"})
    items = entities.list_for("u1", pid, "conditions")
    assert len(items) == 1
    assert items[0]["diagnose"] == "A-korrigiert"   # upsert, nicht Duplikat

def test_array_field_roundtrip(pid):
    entities.create("u1", pid, "medications",
                    {"name": "Metformin", "nebenwirkungen": ["Übelkeit", "Durchfall"]})
    item = entities.list_for("u1", pid, "medications")[0]
    assert item["nebenwirkungen"] == ["Übelkeit", "Durchfall"]

def test_numeric_field_stored_as_number(pid):
    entities.create("u1", pid, "observations",
                    {"parameter": "HbA1c", "wert": 6.4, "einheit": "%", "datum": "2026-05-01"})
    item = entities.list_for("u1", pid, "observations")[0]
    assert item["wert"] == 6.4

def test_batch_create(pid):
    n = entities.batch_create("u1", pid, "observations", [
        {"parameter": "HbA1c", "wert": 7.8, "datum": "2025-03-01"},
        {"parameter": "eGFR", "wert": 93, "datum": "2025-03-01"},
    ])
    assert n == 2
    assert len(entities.list_for("u1", pid, "observations")) == 2

def test_filter_by_q(pid):
    entities.create("u1", pid, "conditions", {"diagnose": "Diabetes mellitus"})
    entities.create("u1", pid, "conditions", {"diagnose": "Hypertonie"})
    items = entities.list_for("u1", pid, "conditions", q="diabet")
    assert len(items) == 1

def test_unknown_entity_raises(pid):
    with pytest.raises(KeyError):
        entities.create("u1", pid, "nonsense", {})

def test_foreign_patient_blocked():
    pid2 = patients.create("u2", {"slug": "b"})
    with pytest.raises(PermissionError):
        entities.create("u1", pid2, "conditions", {"diagnose": "X"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_entities.py -v`
Expected: FAIL.

- [ ] **Step 3: Write `entities.py`** (registry-getrieben, generisch über alle 9 Entitäten)

```python
"""Generischer CRUD über alle Akte-Entitäten — registry-getrieben."""
from __future__ import annotations

import json
from typing import Any

from hydrahive.db._utils import now_iso, uuid7
from hydrahive.db.connection import db
from hydrahive.patientenakte._dates import to_sort_date
from hydrahive.patientenakte.patients import get as _get_patient
from hydrahive.patientenakte.schema import COMMON_FIELDS, ENTITIES


def _spec(entity: str):
    if entity not in ENTITIES:
        raise KeyError(entity)
    return ENTITIES[entity]


def _ensure_owner(user_id: str, pid: str) -> None:
    if _get_patient(user_id, pid) is None:
        raise PermissionError(pid)


def _split(spec, data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    typed = {f: data[f] for f in spec.fields if f in data}
    extra = {f: data[f] for f in spec.array_fields if f in data}
    for f in COMMON_FIELDS:
        if f in data:
            typed[f] = data[f]
    return typed, extra


def create(user_id: str, pid: str, entity: str, data: dict[str, Any]) -> str:
    spec = _spec(entity)
    _ensure_owner(user_id, pid)
    typed, extra = _split(spec, data)
    ext = typed.get("external_id")
    if ext:
        existing = _find_by_external(pid, spec, ext)
        if existing:
            update(user_id, pid, entity, existing, data)
            return existing
    eid, ts = uuid7(), now_iso()
    cols = ["id","patient_id","created_at","updated_at","extra_json","sort_date"]
    vals: list[Any] = [eid, pid, ts, ts, json.dumps(extra) if extra else None,
                       to_sort_date(data.get(spec.date_field)) if spec.date_field else None]
    for k, v in typed.items():
        cols.append(k); vals.append(v)
    ph = ",".join("?" * len(cols))
    with db() as conn:
        conn.execute(f"INSERT INTO {spec.table} ({','.join(cols)}) VALUES ({ph})", vals)
    return eid


def _find_by_external(pid: str, spec, ext: str) -> str | None:
    with db() as conn:
        row = conn.execute(
            f"SELECT id FROM {spec.table} WHERE patient_id=? AND external_id=?", (pid, ext)
        ).fetchone()
    return row["id"] if row else None


def _row_to_dict(spec, row) -> dict[str, Any]:
    out = {k: row[k] for k in row.keys() if k != "extra_json"}
    if row["extra_json"]:
        out.update(json.loads(row["extra_json"]))
    return out


def list_for(user_id: str, pid: str, entity: str, *, q: str | None = None,
             status: str | None = None) -> list[dict[str, Any]]:
    spec = _spec(entity)
    _ensure_owner(user_id, pid)
    sql = f"SELECT * FROM {spec.table} WHERE patient_id=?"
    args: list[Any] = [pid]
    if status and "status" in spec.fields:
        sql += " AND status=?"; args.append(status)
    if q:
        like = " OR ".join(f"{f} LIKE ?" for f in spec.fields)
        sql += f" AND ({like})"; args += [f"%{q}%"] * len(spec.fields)
    sql += " ORDER BY sort_date DESC NULLS LAST, created_at DESC"
    with db() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [_row_to_dict(spec, r) for r in rows]


def get(user_id: str, pid: str, entity: str, eid: str) -> dict[str, Any] | None:
    spec = _spec(entity)
    _ensure_owner(user_id, pid)
    with db() as conn:
        row = conn.execute(
            f"SELECT * FROM {spec.table} WHERE id=? AND patient_id=?", (eid, pid)).fetchone()
    return _row_to_dict(spec, row) if row else None


def update(user_id: str, pid: str, entity: str, eid: str, data: dict[str, Any]) -> bool:
    spec = _spec(entity)
    _ensure_owner(user_id, pid)
    typed, extra = _split(spec, data)
    sets, vals = ["updated_at=?"], [now_iso()]
    for k, v in typed.items():
        sets.append(f"{k}=?"); vals.append(v)
    if extra:
        sets.append("extra_json=?"); vals.append(json.dumps(extra))
    if spec.date_field and spec.date_field in data:
        sets.append("sort_date=?"); vals.append(to_sort_date(data[spec.date_field]))
    vals += [eid, pid]
    with db() as conn:
        cur = conn.execute(
            f"UPDATE {spec.table} SET {','.join(sets)} WHERE id=? AND patient_id=?", vals)
    return cur.rowcount > 0


def delete(user_id: str, pid: str, entity: str, eid: str) -> bool:
    spec = _spec(entity)
    _ensure_owner(user_id, pid)
    with db() as conn:
        cur = conn.execute(
            f"DELETE FROM {spec.table} WHERE id=? AND patient_id=?", (eid, pid))
    return cur.rowcount > 0


def batch_create(user_id: str, pid: str, entity: str, items: list[dict[str, Any]]) -> int:
    for item in items:
        create(user_id, pid, entity, item)
    return len(items)
```

> **Sicherheitshinweis (für code-review/security-audit):** `entity` wird ausschließlich über `ENTITIES`-Registry in Tabellennamen übersetzt (`_spec` wirft `KeyError` bei Unbekanntem) — keine SQL-Injection über `{spec.table}`/`{f}`, da diese nur aus der statischen Registry stammen, nie aus User-Input. Werte gehen immer über Parameter-Bindings. `NULLS LAST` ggf. SQLite-Version prüfen (Step 4).

- [ ] **Step 4: SQLite `NULLS LAST` verifizieren**

Run: `cd core && ~/.venv-cards/bin/python -c "import sqlite3; print(sqlite3.sqlite_version)"`
Expected: ≥ 3.30 (NULLS LAST unterstützt). Falls älter: `ORDER BY sort_date IS NULL, sort_date DESC, created_at DESC`.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_entities.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/src/hydrahive/patientenakte/entities.py core/tests/test_akte_entities.py
git commit -m "feat(akte): generic registry-driven entity CRUD + batch + idempotent upsert"
```

---

### Task 5: Timeline + Summary

**Files:**
- Create: `core/src/hydrahive/patientenakte/views.py`
- Test: `core/tests/test_akte_views.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from hydrahive.patientenakte import patients, entities, views

@pytest.fixture
def pid():
    p = patients.create("u1", {"slug": "alex"})
    entities.create("u1", p, "conditions", {"diagnose": "Diabetes", "diagnostiziert_am": "2021-05-01"})
    entities.create("u1", p, "events", {"typ": "OP", "datum_von": "2024-11-20", "einrichtung": "St. Katharinen"})
    entities.create("u1", p, "observations", {"parameter": "HbA1c", "wert": 6.4, "datum": "2026-05-01"})
    return p

def test_timeline_chronological_desc(pid):
    tl = views.timeline("u1", pid)
    dates = [e["sort_date"] for e in tl]
    assert dates == sorted(dates, reverse=True)   # neueste zuerst
    assert tl[0]["entity"] == "observations"      # 2026 oben

def test_timeline_entries_have_label_and_entity(pid):
    e = views.timeline("u1", pid)[0]
    assert "label" in e and "entity" in e and "record" in e

def test_summary_counts(pid):
    s = views.summary("u1", pid)
    assert s["conditions"] == 1
    assert s["events"] == 1
    assert s["observations"] == 1
    assert s.get("medications", 0) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_views.py -v`
Expected: FAIL.

- [ ] **Step 3: Write `views.py`**

```python
"""Aggregierte Sichten: Timeline + Summary über alle Entitäten."""
from __future__ import annotations

from typing import Any

from hydrahive.db.connection import db
from hydrahive.patientenakte.entities import _row_to_dict
from hydrahive.patientenakte.patients import get as _get_patient
from hydrahive.patientenakte.schema import ENTITIES


def summary(user_id: str, pid: str) -> dict[str, int]:
    if _get_patient(user_id, pid) is None:
        raise PermissionError(pid)
    out: dict[str, int] = {}
    with db() as conn:
        for key, spec in ENTITIES.items():
            row = conn.execute(
                f"SELECT COUNT(*) AS c FROM {spec.table} WHERE patient_id=?", (pid,)).fetchone()
            out[key] = row["c"]
    return out


def timeline(user_id: str, pid: str) -> list[dict[str, Any]]:
    if _get_patient(user_id, pid) is None:
        raise PermissionError(pid)
    entries: list[dict[str, Any]] = []
    with db() as conn:
        for key, spec in ENTITIES.items():
            rows = conn.execute(
                f"SELECT * FROM {spec.table} WHERE patient_id=? AND sort_date IS NOT NULL",
                (pid,)).fetchall()
            for r in rows:
                entries.append({"entity": key, "label": spec.label,
                                "sort_date": r["sort_date"], "record": _row_to_dict(spec, r)})
    entries.sort(key=lambda e: e["sort_date"], reverse=True)
    return entries
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_views.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/patientenakte/views.py core/tests/test_akte_views.py
git commit -m "feat(akte): timeline + summary aggregation"
```

---

### Task 6: REST-API + Auth + Registrierung

**Files:**
- Create: `core/src/hydrahive/api/routes/patientenakte.py`
- Modify: `core/src/hydrahive/api/main.py` (Router registrieren — Muster wie `research_apis` Router)
- Test: `core/tests/test_akte_api.py`

- [ ] **Step 1: Lies das bestehende Auth-/Router-Muster**

Lies `api/routes/fhir.py` (require_auth-Nutzung), `api/middleware/auth.py` (`require_auth` → `(username, role)`, `hhk_`-Keys), `api/main.py` (wie `research_apis`/`fhir` Router eingehängt sind). Übernimm das Muster 1:1.

- [ ] **Step 2: Write the failing test** (TestClient)

```python
import pytest
from fastapi.testclient import TestClient
from hydrahive.api.main import app

# Annahme: es existiert eine Test-Auth-Override-Fixture wie bei test für andere Routes.
# Falls nicht vorhanden: require_auth via app.dependency_overrides auf ("u1","user") setzen.

@pytest.fixture
def client():
    from hydrahive.api.middleware.auth import require_auth
    app.dependency_overrides[require_auth] = lambda: ("u1", "user")
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_create_patient_and_list(client):
    r = client.post("/api/health/patientenakte/patients", json={"slug": "alex", "name": "Molke"})
    assert r.status_code == 200
    pid = r.json()["id"]
    r2 = client.get("/api/health/patientenakte/patients")
    assert any(p["id"] == pid for p in r2.json())

def test_create_condition_via_api(client):
    pid = client.post("/api/health/patientenakte/patients", json={"slug": "a"}).json()["id"]
    r = client.post(f"/api/health/patientenakte/patients/{pid}/conditions",
                    json={"external_id": "k75", "diagnose": "Leberabszess", "icd_code": "K75.0"})
    assert r.status_code == 200
    items = client.get(f"/api/health/patientenakte/patients/{pid}/conditions").json()
    assert items[0]["icd_code"] == "K75.0"

def test_idempotent_via_api(client):
    pid = client.post("/api/health/patientenakte/patients", json={"slug": "a"}).json()["id"]
    for _ in range(2):
        client.post(f"/api/health/patientenakte/patients/{pid}/observations/batch",
                    json={"items": [{"external_id": "h1", "parameter": "HbA1c", "wert": 6.4, "datum": "2026-05-01"}]})
    assert len(client.get(f"/api/health/patientenakte/patients/{pid}/observations").json()) == 1

def test_timeline_and_summary_endpoints(client):
    pid = client.post("/api/health/patientenakte/patients", json={"slug": "a"}).json()["id"]
    client.post(f"/api/health/patientenakte/patients/{pid}/conditions", json={"diagnose": "X", "diagnostiziert_am": "2020-01-01"})
    assert client.get(f"/api/health/patientenakte/patients/{pid}/summary").json()["conditions"] == 1
    assert len(client.get(f"/api/health/patientenakte/patients/{pid}/timeline").json()) == 1

def test_unknown_entity_404(client):
    pid = client.post("/api/health/patientenakte/patients", json={"slug": "a"}).json()["id"]
    assert client.get(f"/api/health/patientenakte/patients/{pid}/nonsense").status_code == 404
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_api.py -v`
Expected: FAIL (routes 404).

- [ ] **Step 4: Write `patientenakte.py` routes** (generisch über `{entity}`)

```python
"""REST-API der Patientenakte. Token/JWT-Auth via require_auth."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from hydrahive.api.middleware.auth import require_auth
from hydrahive.patientenakte import entities, patients, views
from hydrahive.patientenakte.schema import ENTITIES

router = APIRouter(prefix="/api/health/patientenakte", tags=["patientenakte"])
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _entity_or_404(entity: str) -> None:
    if entity not in ENTITIES:
        raise HTTPException(404, f"Unbekannte Entität: {entity}")


@router.get("/patients")
async def list_patients(auth: Auth) -> list[dict[str, Any]]:
    return patients.list_for(auth[0])


@router.post("/patients")
async def create_patient(data: dict[str, Any], auth: Auth) -> dict[str, str]:
    return {"id": patients.create(auth[0], data)}


@router.get("/patients/{pid}")
async def get_patient(pid: str, auth: Auth) -> dict[str, Any]:
    p = patients.get(auth[0], pid)
    if p is None:
        raise HTTPException(404, "Patient nicht gefunden")
    p["counts"] = views.summary(auth[0], pid)
    return p


@router.patch("/patients/{pid}")
async def update_patient(pid: str, data: dict[str, Any], auth: Auth) -> dict[str, bool]:
    return {"ok": patients.update(auth[0], pid, data)}


@router.delete("/patients/{pid}")
async def delete_patient(pid: str, auth: Auth) -> dict[str, bool]:
    return {"ok": patients.delete(auth[0], pid)}


@router.get("/patients/{pid}/timeline")
async def timeline(pid: str, auth: Auth) -> list[dict[str, Any]]:
    return views.timeline(auth[0], pid)


@router.get("/patients/{pid}/summary")
async def summary(pid: str, auth: Auth) -> dict[str, int]:
    return views.summary(auth[0], pid)


@router.get("/patients/{pid}/{entity}")
async def list_entity(pid: str, entity: str, auth: Auth,
                      q: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    _entity_or_404(entity)
    return entities.list_for(auth[0], pid, entity, q=q, status=status)


@router.post("/patients/{pid}/{entity}")
async def create_entity(pid: str, entity: str, data: dict[str, Any], auth: Auth) -> dict[str, str]:
    _entity_or_404(entity)
    return {"id": entities.create(auth[0], pid, entity, data)}


@router.post("/patients/{pid}/{entity}/batch")
async def batch_entity(pid: str, entity: str, body: dict[str, Any], auth: Auth) -> dict[str, int]:
    _entity_or_404(entity)
    return {"created": entities.batch_create(auth[0], pid, entity, body.get("items", []))}


@router.get("/patients/{pid}/{entity}/{eid}")
async def get_entity(pid: str, entity: str, eid: str, auth: Auth) -> dict[str, Any]:
    _entity_or_404(entity)
    rec = entities.get(auth[0], pid, entity, eid)
    if rec is None:
        raise HTTPException(404, "Eintrag nicht gefunden")
    return rec


@router.patch("/patients/{pid}/{entity}/{eid}")
async def update_entity(pid: str, entity: str, eid: str, data: dict[str, Any], auth: Auth) -> dict[str, bool]:
    _entity_or_404(entity)
    return {"ok": entities.update(auth[0], pid, entity, eid, data)}


@router.delete("/patients/{pid}/{entity}/{eid}")
async def delete_entity(pid: str, entity: str, eid: str, auth: Auth) -> dict[str, bool]:
    _entity_or_404(entity)
    return {"ok": entities.delete(auth[0], pid, entity, eid)}
```

> **Routing-Reihenfolge beachten:** `/patients/{pid}/timeline` und `/summary` MÜSSEN vor `/patients/{pid}/{entity}` definiert sein (sonst fängt `{entity}` „timeline" ab). In FastAPI gewinnt die zuerst registrierte Route — Reihenfolge oben ist korrekt. Test `test_timeline_and_summary_endpoints` deckt das ab.

- [ ] **Step 5: Register router in `api/main.py`**

Wie `research_apis`/`fhir`: `from hydrahive.api.routes import patientenakte` + `app.include_router(patientenakte.router)`.

- [ ] **Step 6: Run test to verify it passes**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_api.py -v`
Expected: PASS.

- [ ] **Step 7: PermissionError → 403/404 mappen**

`entities`/`views` werfen `PermissionError` bei fremdem Patienten. Sicherstellen, dass das als 404 (nicht 500) rausgeht — entweder Exception-Handler in `main.py` (prüfen ob existiert) oder in den Routes fangen. Test ergänzen:
```python
def test_foreign_patient_404(client):
    # u1 legt an, simulierter u2 darf nicht
    pid = client.post("/api/health/patientenakte/patients", json={"slug":"a"}).json()["id"]
    app.dependency_overrides[require_auth] = lambda: ("u2", "user")
    assert client.get(f"/api/health/patientenakte/patients/{pid}/conditions").status_code == 404
```

- [ ] **Step 8: Commit**

```bash
git add core/src/hydrahive/api/routes/patientenakte.py core/src/hydrahive/api/main.py core/tests/test_akte_api.py
git commit -m "feat(akte): REST API (patients + generic entities + batch + timeline/summary)"
```

---

### Task 7: Befüll-Skill für Agenten

**Files:**
- Create: `core/src/hydrahive/skills/system_defaults/medical-akte.md`
- Test: manuell (Skill wird beim Start via `install_system_defaults()` installiert)

- [ ] **Step 1: Write the skill** (Frontmatter wie andere `system_defaults/*.md`: name/description/when_to_use/tools_required)

Inhalt: Wie ein Agent die Akte über die REST-API befüllt — Endpoints, Auth (Bearer `hhk_`-Token), `external_id` für Idempotenz, Batch für Laborwerte, die 9 `{entity}`-Keys + Feldlisten, `quelle`/`confidence`/`verifiziert`-Konvention. Konkrete `fetch_url`-Beispiele (POST mit JSON-Body), analog zum bestehenden `medical-research.md`.

- [ ] **Step 2: Verify frontmatter parses**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/ -k skill -q` (falls Skill-Lade-Tests existieren) — sonst: `~/.venv-cards/bin/python -c "from hydrahive.skills... import load; ..."` (Lade-Pfad aus bestehendem Skill-Test ableiten).

- [ ] **Step 3: Commit**

```bash
git add core/src/hydrahive/skills/system_defaults/medical-akte.md
git commit -m "feat(akte): medical-akte skill — how agents fill the record via REST"
```

---

### Task 8: Prototyp-Migration (YAML/CSV → Akte)

**Files:**
- Create: `core/scripts/import_akte_prototype.py`
- Test: `core/tests/test_akte_import.py`

- [ ] **Step 1: Write the failing test** (mit Mini-Fixtures, die die reale YAML-Struktur spiegeln)

```python
import textwrap
from pathlib import Path
import pytest
from hydrahive.patientenakte import patients, entities
from hydrahive.scripts_akte import import_akte  # Wrapper-Funktion im Skript

def _write(tmp: Path, name: str, content: str):
    (tmp / name).write_text(textwrap.dedent(content), encoding="utf-8")

def test_import_maps_diagnosen_and_medications(tmp_path):
    _write(tmp_path, "stammdaten.yaml", """
        name: "Molke"
        vorname: "Alexander"
        geburtsdatum: "1970-07-31"
        adresse: {strasse: "Hahnenkammstr. 11", plz: "60388", ort: "Frankfurt am Main", land: "Deutschland"}
        versicherung: {krankenkasse: {name: "TK"}}
    """)
    _write(tmp_path, "diagnosen.yaml", """
        diagnosen:
          - diagnose: "Diabetes mellitus Typ 2"
            icd_code: "E11"
            status: "chronisch"
            quelle: "abgeleitet"
    """)
    _write(tmp_path, "medikamente.yaml", """
        medikamente:
          - {name: "Metformin", wirkstoff: "Metformin", atc: "A10BA02"}
        historische:
          - {name: "Insulin", wirkstoff: "Insulin", atc: "A10AE05"}
    """)
    pid = import_akte("u1", "alex", tmp_path)
    p = patients.get("u1", pid)
    assert p["name"] == "Molke"
    assert p["adresse"]["ort"] == "Frankfurt am Main"
    conds = entities.list_for("u1", pid, "conditions")
    assert any(c["icd_code"] == "E11" for c in conds)
    meds = {m["name"]: m["status"] for m in entities.list_for("u1", pid, "medications")}
    assert meds["Metformin"] == "aktuell"
    assert meds["Insulin"] == "historisch"

def test_import_is_idempotent(tmp_path):
    _write(tmp_path, "diagnosen.yaml", """
        diagnosen:
          - {diagnose: "X", icd_code: "E11", status: "chronisch"}
    """)
    pid = import_akte("u1", "alex", tmp_path)
    import_akte("u1", "alex", tmp_path)   # zweiter Lauf
    assert len(entities.list_for("u1", pid, "conditions")) == 1
```

> Idempotenz: Das Import-Skript vergibt deterministische `external_id` (z.B. `proto:{slug}:conditions:{index}` oder ein Hash über stabile Felder), und der Patient wird per `slug`+owner wiedergefunden statt neu angelegt.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_import.py -v`
Expected: FAIL.

- [ ] **Step 3: Write `import_akte_prototype.py`**

Mapping gemäß Lastenheft §6:
- `stammdaten.yaml` → `patients.create/update` (nested dicts direkt durchreichen: adresse/versicherung/notfall_kontakt→notfallkontakt).
- `diagnosen.yaml` (`diagnosen:`) → conditions; deterministische `external_id`.
- `medikamente.yaml` (`medikamente:` → status "aktuell", `historische:` → status "historisch"; Feld `atc`→`atc_code`).
- `ereignisse_klinik.yaml` (`ereignisse:` → events; `datum` „X bis Y" splitten → datum_von/datum_bis; `ort`→einrichtung; `nebendiagnosen`/`therapie`→verlauf+arrays; `entlassmedikation_*:`→ als events.extra_json oder eigene medications mit status "entlassung").
- `bildgebung.yaml` (`untersuchungen:` → imaging; `typ`→modalitaet, `serien`→serien_beschreibung, `bilder`→anzahl_bilder, `pfad`→dicom_pfad, `kontext`→befund).
- `allergien.yaml` (`allergien:` → allergies; leer bei alex → 0 Einträge, kein Fehler).
- `aerzte.yaml` (`hausaerztin:`→practitioner rolle=hausarzt; `fachaerzte:`→rolle=facharzt).
- `labor_werte.csv` → observations Batch (eine Spalte = parameter; Wert numerisch→`wert`, sonst `wert_text`). CSV-Pfad per glob suchen (liegt nicht in `akten/<slug>/`).
- `ZUSAMMENFASSUNG.md` + andere `*.md` → notes (titel=Dateiname, inhalt=Markdown, kategorie="zusammenfassung").

Exponiere `import_akte(user_id, slug, dir_path) -> pid` als importierbare Funktion (in `hydrahive/scripts_akte.py` oder als Funktion im Skript, vom Test importierbar). `if __name__ == "__main__":` CLI-Wrapper.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd core && ~/.venv-cards/bin/python -m pytest tests/test_akte_import.py -v`
Expected: PASS.

- [ ] **Step 5: Trockenlauf gegen reale Daten dokumentieren** (NICHT auf .22 Prod-DB)

Reale YAMLs liegen im Projekt-Workspace (`hh_read_file`). Für den echten Import auf .22 entscheidet Till Zeitpunkt/Patient. Hier nur: Skript-Aufruf + erwartete Counts dokumentieren.

- [ ] **Step 6: Commit**

```bash
git add core/scripts/import_akte_prototype.py core/tests/test_akte_import.py
git commit -m "feat(akte): YAML/CSV prototype migration script"
```

---

### Task 9: Phase-1-Abschluss

- [ ] **Step 1: Full suite grün**

Run: `cd core && ~/.venv-cards/bin/python -m pytest -q`
Expected: alle grün (inkl. der ~6 neuen Test-Dateien).

- [ ] **Step 2: requesting-code-review** (Skill) über den Phase-1-Diff. Erwartete Schwerpunkte: SQL-Injection-Fläche der generischen Routes (Registry-Whitelist), Owner-Isolation lückenlos, Idempotenz-Race.

- [ ] **Step 3: Findings einarbeiten** (receiving-code-review Skill).

- [ ] **Step 4: Merge nach main** (finishing-a-development-branch). Till deployed auf .22, testet die API (z.B. `curl` mit `hhk_`-Token), bestätigt.

---

# PHASE 2 — UI (Roadmap)

> Detaillierter Plan via `writing-plans` zu Phasenbeginn. Form hängt von realen API-Shapes aus Phase 1 ab.

**Files (geplant):**
- `frontend/src/features/health/api.ts` — `akteApi`-Client (Patients/Entities/Timeline/Summary).
- `frontend/src/features/health/views/akte/PatientPicker.tsx` — Dropdown/Kacheln (alex, bibs).
- `.../akte/AkteDashboard.tsx` — Kopf (Stammdaten + „rote Fakten": aktive Diagnosen/Allergien/Dauermedikation) + Count-Kacheln.
- `.../akte/AkteTimeline.tsx` — chronologisch, filterbar nach Entität.
- `.../akte/EntityList.tsx` — generische sortier-/filterbare Tabelle (registry-analog im Frontend).
- `.../akte/LabCharts.tsx` — Trend-Charts (HbA1c, eGFR …) mit Referenzbereich-Markierung (Lib wie bestehende TrendChart/SleepChart wiederverwenden).
- `.../akte/VerifyBadge.tsx` — gelber Punkt für `verifiziert=false` + „Verifizieren"-Button (PATCH).
- Modify: `HealthSidebar.tsx` — neue Sektion „Patientenakte" (primär, oben) + bestehende Sektionen unter „Kassendaten / Import (eGA/FHIR)" umbenennen/gruppieren.
- Modify: `HealthPage.tsx` — neue Routen `/health/akte`, `/health/akte/:pid/...`.

**Akzeptanz:** Multi-Patient-Auswahl; Dashboard+Timeline+Summary; Detail-Listen mit Lab-Charts; unverifizierte Einträge markiert.

---

# PHASE 3 — Dokumente + Volltextsuche (Roadmap)

> OCR liefert der Agent (kein Tesseract). Server speichert + indexiert.

**Files (geplant):**
- `core/src/hydrahive/patientenakte/documents.py` — Datei-Upload-Storage (Filesystem unter `settings.data_dir/patientenakte/docs/{patient}/`, 0600), MIME/Größen-Validierung, Download.
- Migration `024_akte_fts.sql` — SQLite **FTS5**-Tabelle `akte_fts(entity, entity_id, patient_id, content)` + Trigger/Service, der bei jedem create/update den durchsuchbaren Text einspeist (inkl. `documents.ocr_text`).
- `core/src/hydrahive/patientenakte/search.py` — `search(user_id, pid, q)` über FTS5 statt `LIKE`.
- Routes: `POST /patients/{pid}/documents/{id}/file` (multipart), `GET .../file` (download), `GET /patients/{pid}/search?q=`.
- Frontend: Dokumente-View (Liste, OCR-Volltext einblendbar, Vorschau, Download) + globale Suche.

**Entscheidung Phase 3:** FTS5-Indexpflege (Trigger vs. Service-seitig) — Service-seitig bevorzugt (kontrollierbar, kein SQL-Trigger-Magic). Wechselwirkung mit Phase-4-Verschlüsselung (s.u.) hier schon mitdenken.

---

# PHASE 4 — DSGVO (Roadmap)

**Files (geplant):**
- Migration `025_akte_audit.sql` — `akte_audit(id, ts, user_id, action, entity, entity_id, patient_id, detail)`.
- `core/src/hydrahive/patientenakte/audit.py` — `log(...)`, in jede Lese-/Schreiboperation eingehängt (Lastenheft NFR §5: jede Operation loggen).
- `core/src/hydrahive/patientenakte/crypto_fields.py` — spaltenweise Ver-/Entschlüsselung via `credentials/_crypto.py` (Umfang gem. Entscheidung (a)/(b)/(c) oben).
- `core/src/hydrahive/patientenakte/export.py` — Vollexport JSON (+ PDF: Lib prüfen, ggf. reportlab/weasyprint via context7).
- Routes: `GET /patients/{pid}/export?format=json|pdf`, `DELETE /patients/{pid}` (bereits da, hier Audit + bestätigte Kaskade).
- **security-audit Skill** über die ganze Akte (PHI, Auth, Injection, Audit-Vollständigkeit, Crypto).

**Entscheidung Phase 4:** Verschlüsselung-vs-Suche (oben dokumentiert) final mit Till + security-audit.

---

## Self-Review (gegen Lastenheft)

| Lastenheft | Abgedeckt durch |
|---|---|
| §1.2 Multi-Patient | Task 1 (akte_patient.owner_user_id), Task 3 |
| §2 10 Entitäten, Basis-Felder | Task 1/2 (gemeinsame Spalten + 9 Tabellen; „Patient" = 10.) |
| §2.4 Labor Batch | Task 4 (batch_create), Task 6 (/batch) |
| §3 REST-API Token-Auth | Task 6 (require_auth + hhk_), Task 7 |
| §3 external_id Idempotenz | Task 4 (upsert), Task 6/8 (Tests) |
| §3.3 Dokumente + OCR | Phase 3 |
| §3.4 Timeline/Summary/Search/Export | Task 5 (timeline/summary), Phase 3 (search), Phase 4 (export) |
| §4 UI | Phase 2 |
| §4.5 Quellen-Kennzeichnung | Task 1 (verifiziert), Phase 2 (VerifyBadge) |
| §5 Datenschutz/Audit/Export/Löschung | Phase 4 |
| §5 Idempotenz | Task 4 |
| §6 Migration Prototyp | Task 8 |
| §7 Akzeptanzkriterien | über alle Phasen |

**Bekannte offene Punkte (bewusst):** PDF-Export-Lib (Phase 4, context7), ICD/ATC-Validierung (Lastenheft §5 „optional" — v1 weggelassen, später), Verschlüsselung-vs-Suche (Phase 4).

---

## Anhang A — Vorschlag SPEC-Sektion (Entwurf, braucht Tills OK + Standalone-Commit)

> Platzierung: in `SPEC.md` im Health-Extension-Bereich, nach den bestehenden Health/eGA/FHIR-Absätzen.

```markdown
## Patientenakte (Health-Extension)

Strukturierte, persistente, multi-Patient-fähige elektronische Patientenakte (ePA-light)
als Kern der Health-Extension. Abgegrenzt von der read-only eGA/FHIR-Importschicht
(Kassendaten): die Patientenakte ist die schreibbare, von Agenten und Nutzer befüllbare
Akte.

- **Datenmodell:** FHIR-R4-angelehnt, pragmatisch relational (eigene SQLite-Tabellen,
  kein FHIR-Server). Entitäten: Patient, Diagnose (Condition), Medikament,
  Laborwert (Observation), Ereignis/Prozedur (Encounter), Bildgebung (ImagingStudy),
  Allergie, Arzt (Practitioner), Dokument (DocumentReference), Notiz. Jeder Datensatz
  trägt quelle/confidence/verifiziert (manuell vs. KI-extrahiert) + external_id (Idempotenz).
- **Befüllung:** Token-geschützte REST-API (JSON), damit Agenten Datensätze
  anlegen/aktualisieren (CRUD + Batch für Laborwerte). Idempotenz über external_id.
- **Dokumente:** Upload (PDF/Bild/DICOM-Verweis) + vom Agenten geliefertem OCR-Text,
  Volltextsuche.
- **UI:** Eigener Health-Bereich „Patientenakte" — Patienten-Auswahl, Dashboard,
  Timeline, Detail-Listen, Lab-Trend-Charts, Quellen-/Verifiziert-Markierung.
- **Datenschutz (Art. 9 DSGVO):** Verschlüsselung-at-rest sensibler Felder,
  Zugriffskontrolle pro Nutzer, Audit-Log, Export + vollständige Löschung pro Patient.

Nicht-Ziele (v1): vollwertiger FHIR-Server, automatische med. Befundung,
KIM/TI-Anbindung, DICOM-Bildanzeige im Browser.
```
