# Patientenakte Phase 2 — UI Plan
> Stand: 2026-05-30 | Status: Draft | Owner: castielle | Branch: feat/castiele

## Die Anforderung

**Single-User Akte:** Jeder HydraHive-User hat seine eigene Patientenakte — keine Multi-Patient-Auswahl.
**Integration in Health:** Die `/health`-Seite wird die komplette Patientenakte — nicht nur ein Import-Interface.
**Was bisher war:** Read-only eGA/FHIR-Daten anzeigen. Zu wenig.
**Was sein soll:** Eigene Akte lesen + schreiben + auswerten. eGA/FHIR als optionaler Import darunter.

---

## Architektur-Entscheidung

```
/health                    ← NEU: primäre Patientenakte (eigene Daten, schreibbar)
/health/uebersicht        ← AKTE-Dashboard (Stammdaten, Counts, rote Fakten)
/health/timeline          ← AKTE-Timeline (chronologisch, filterbar, alle Entitäten)
/health/conditions        ← Diagnosen (lesen/schreiben)
// ... 9 Entity-Listen analog
/health/import             ← eGA/FHIR-Import (bisherige Views, readonly)
```

**Kein zweiter Route-Baum.** Die Health-Seite selbst wird die Akte.
`HealthSidebar` bekommt eine "Meine Akte"-Sektion oben, "Import" darunter.
Bestehende eGA/FHIR-Routen bleiben funktional — werden nur in eine `ImportSection` zusammengefasst.

**Auth:** `auth.user_id` kommt aus dem JWT — kein PatientPicker nötig.
Der Server kennt pro User genau eine Akte (eine `akte_patient`-Zeile mit `owner_user_id = auth.user_id`).

---

## Neue HealthSidebar-Struktur

```tsx
const SECTIONS: Section[] = [
  {
    title: "Meine Akte",
    items: [
      { to: "/health/uebersicht", icon: "🗂", label: "Übersicht" },
      { to: "/health/timeline", icon: "📅", label: "Zeitstrahl" },
      { to: "/health/conditions", icon: "🔴", label: "Diagnosen" },
      { to: "/health/medications", icon: "💊", label: "Medikamente" },
      { to: "/health/observations", icon: "🧪", label: "Laborwerte" },
      { to: "/health/allergies", icon: "🤧", label: "Allergien" },
      { to: "/health/events", icon: "📋", label: "Ereignisse" },
      { to: "/health/imaging", icon: "🩻", label: "Bildgebung" },
      { to: "/health/practitioners", icon: "👨‍⚕️", label: "Ärzte" },
      { to: "/health/documents", icon: "📄", label: "Dokumente" },
      { to: "/health/notes", icon: "📝", label: "Notizen" },
    ],
  },
  {
    title: "Import",
    items: [
      { to: "/health/import", icon: "📥", label: "eGA / FHIR Import" },
    ],
  },
]
```

---

## API-Änderungen (Backend)

### Route: Kein `patient_id` mehr nötig (User = Owner)
```
GET    /health/patientenakte                   → eigene Akte oder 404
POST   /health/patientenakte                   → Akte anlegen (einmalig)
PATCH  /health/patientenakte                   → Stammdaten updaten
GET    /health/patientenakte/summary           → Counts
GET    /health/patientenakte/timeline           → Timeline
GET    /health/patientenakte/{entity}           → Entity-Liste
POST   /health/patientenakte/{entity}          → Neuer Eintrag
PATCH  /health/patientenakte/{entity}/{id}      → Edit
DELETE /health/patientenakte/{entity}/{id}      → Delete
```

**Backend-Änderung:** `entities.py` bekommt einen `get_own()` / `create_own()` Wrapper
der `auth.user_id` als `owner_user_id` nimmt statt `patient_id`.
`patients.py` wird obsolet (oder behält die Helpers für Stammdaten).

### Neuer Endpoint
```
GET    /health/patientenakte                   → 200 { id, name, vorname, geburtsdatum, geschlecht, versicherung, counts }
                                                  oder 404 wenn keine Akte existiert
POST   /health/patientenakte                   → 201 { id } — Akte anlegen
```

---

## Frontend-Tasks (9 Stück)

### Task 1: HealthSidebar umbauen
- "Patientenakte"-Sektion → "Meine Akte"
- Neue Items für alle 9 Entities + Timeline
- "Import"-Sektion darunter

### Task 2: HealthPage UebersichtView → AkteDashboard
- `UebersichtView.tsx` wird das Akte-Dashboard
- Prüft `GET /health/patientenakte` → 404 → Zeigt "Akte anlegen"-Prompt
- 200 → Zeigt Stammdaten + Counts + rote Fakten

### Task 3: AkteDashboard-Business-Logic
- Wenn keine Akte → Zeige Hero mit "Meine Akte anlegen"-Formular (name, vorname, geburtsdatum, geschlecht)
- Wenn Akte existiert → Dashboard mit:
  - Stammdaten links
  - Count-Kacheln (conditions, medications, observations, allergies, ...)
  - Aktive Diagnosen (conditions.status='aktuell')
  - Allergien
  - Dauermedikation

### Task 4: Timeline in ZeitstrahlView
- `ZeitstrahlView.tsx` wird Akte-Timeline
- `GET /health/patientenakte/timeline`
- Filter-Toggles für alle 9 Entity-Typen
- VerifyBadge (● grün/orange) je Eintrag

### Task 5: Alle 9 Entity-Listen
- `DiagnosenView.tsx`, `MedikamenteView.tsx`, `LaborwerteView.tsx` etc.
- Werden komplett neu gebaut für Akte (nicht mehr eGA/FHIR)
- Generische Komponente `AkteEntityList.tsx` mit `entity`-Prop

### Task 6: LabCharts in LaborwerteView
- `LaborwerteView.tsx` wird AkteLabCharts
- Gruppiert Observations nach `parameter`
- Recharts LineChart mit Referenzbereichen

### Task 7: AkteApi erweitern
- `akteApi.getOwn()` → GET /health/patientenakte
- `akteApi.createOwn(data)` → POST /health/patientenakte
- Alle Entity-Operationen (list, create, update, delete)
- Timeline + Summary

### Task 8: VerifyBadge + Inline-Verify
- `VerifyBadge.tsx` (● grün wenn verifiziert, ● orange wenn nicht)
- In Timeline und EntityList eingebaut
- Klick → PATCH `verifiziert=1`

### Task 9: Import-Sektion (eGA/FHIR)
- `/health/import` Route
- Zeigt die bisherigen eGA/FHIR-Views (EgaImportButton, FhirImportButton)
- Daten aus dem Import werden NICHT in die Akte geschrieben (nur angezeigt wie bisher)
- Optional: "In Akte übernehmen"-Button pro Record

---

## Akzeptanzkriterien

- [ ] Health-Seite zeigt eigene Patientenakte — nicht eGA-Daten
- [ ] Akte anlegen und sofort Stammdaten sehen
- [ ] Alle 9 Entity-Typen lesen + schreiben
- [ ] Timeline chronologisch, nach Typ filterbar
- [ ] Unverifizierte Einträge orange markiert, Klick→verifizieren
- [ ] Labwerte als Trend-Charts (HbA1c, eGFR etc.)
- [ ] eGA/FHIR-Import erreichbar unter /health/import (bestehende Funktionalität)
- [ ] Kein PatientPicker — alles anhand des eingeloggten Users

---

## Backend-Änderungen (minmal)

`patientenakte/entities.py` bekommt:
```python
def get_own(user_id: str, entity: str) -> list[dict]: ...
def create_own(user_id: str, entity: str, data: dict) -> str: ...
def update_own(user_id: str, entity: str, eid: str, data: dict) -> bool: ...
def delete_own(user_id: str, entity: str, eid: str) -> bool: ...
def timeline_own(user_id: str) -> list[dict]: ...
def summary_own(user_id: str) -> dict: ...
```

`patients.py` bleibt als Stammdaten-Helper, wird aber um `get_own(user_id)` / `create_own(user_id, data)` reduziert.

Route in `patientenakte.py`:
- `GET /` → `patients.get_own(auth.user_id)` oder 404
- `POST /` → `patients.create_own(auth.user_id, data)` → 201
- `GET /timeline` → `entities.timeline_own(auth.user_id)`
- `GET /summary` → `entities.summary_own(auth.user_id)`
- `GET /{entity}` → `entities.get_own(auth.user_id, entity)`
- `POST /{entity}` → `entities.create_own(auth.user_id, entity, data)`
- `PATCH /{entity}/{eid}` → `entities.update_own(auth.user_id, entity, eid, data)`
- `DELETE /{entity}/{eid}` → `entities.delete_own(auth.user_id, entity, eid, data)`