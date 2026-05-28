# Design: Digitale Patientenakte

**Datum:** 2026-05-28
**Status:** Bereit zur Implementierung

---

## Problem

HydraHive hat bereits Apple Health Daten (Schritte, Schlaf, Herzfrequenz), aber keine strukturierte Ansicht für medizinische Patientendaten. Till hat seine komplette Patientenakte als FHIR R4 JSON Export aus der TK-App. Diese Daten sollen importierbar, durchsuchbar und per KI auswertbar sein — als vollständiger digitaler Aktenschrank.

---

## Ziele

1. FHIR R4 JSON aus der TK-App importieren und mergen
2. Alle Ressourcentypen (Diagnosen, Medikamente, Laborwerte, etc.) in der Health-Sektion anzeigen
3. KI-Assistent der Fragen zur Akte beantworten kann
4. Datenschutz: alle Daten strikt an `user_id` gebunden

---

## Nicht-Ziele

- Direkte TK-API-Anbindung (kein live-Sync, manueller JSON-Upload reicht)
- Medizinische Diagnosen durch die KI (nur Erklärungen was in der Akte steht)
- PDF-Import oder OCR
- Mehrbenutzer-Ansichten (jeder sieht nur seine eigenen Daten)

---

## Architektur

### Datenschicht

**Neue Tabelle `fhir_resources`** (Migration `021_fhir_resources.sql`):

```sql
CREATE TABLE fhir_resources (
    id            TEXT PRIMARY KEY DEFAULT (uuid7()),
    user_id       TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id   TEXT NOT NULL,
    resource_json TEXT NOT NULL,
    imported_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, resource_type, resource_id)
);
CREATE INDEX idx_fhir_user_type ON fhir_resources(user_id, resource_type);
```

**Sync-Semantik beim Import:**
- Bestehende Ressource (gleiche `user_id` + `resource_type` + `resource_id`) → UPDATE
- Neue Ressource → INSERT
- Nicht im neuen Export enthaltene Ressourcen → bleiben erhalten (kein Datenverlust)

**FHIR-Ressourcentypen → UI-Kategorien:**

| FHIR `resourceType` | Sidebar-Kategorie |
|---|---|
| `Condition` | Diagnosen |
| `MedicationRequest`, `MedicationStatement` | Medikamente |
| `Observation` | Laborwerte |
| `AllergyIntolerance` | Allergien |
| `Immunization` | Impfungen |
| `Procedure` | Eingriffe |
| `Encounter` | Arztbesuche |
| `DiagnosticReport` | Befunde |
| `DocumentReference` | Dokumente |
| `Patient` | Stammdaten (Übersicht) |
| Unbekannte Typen | gespeichert, nicht angezeigt |

---

### Backend

**Neue Dateien:**

```
core/src/hydrahive/
├── db/fhir.py                  # upsert_bundle, query_by_type, query_all, delete_by_user, summary
├── api/routes/fhir.py          # Endpoints
└── tools/fhir_data.py          # Agent-Tool
```

**API-Endpoints** (alle auth-geschützt, user_id aus JWT):

| Method | Path | Beschreibung |
|---|---|---|
| `POST` | `/api/health/fhir/import` | FHIR Bundle importieren/mergen |
| `GET` | `/api/health/fhir/resources/:type` | Ressourcen einer Kategorie abrufen |
| `GET` | `/api/health/fhir/summary` | Zusammenfassung aller Kategorien (für Übersicht) |
| `GET` | `/api/health/fhir/timeline` | Alle Ereignisse chronologisch sortiert |

**Import-Response:**
```json
{
  "imported": 47,
  "updated": 12,
  "skipped": 0,
  "errors": []
}
```

**Agent-Tool `query_fhir_data`** (`tools/fhir_data.py`):

```python
# Schema:
{
  "resource_types": ["Condition", "Observation"],  # optional, default: alle
  "search_text": "HbA1c"                           # optional Volltextsuche im JSON
}
# Returns: formatierte Textzusammenfassung der gefundenen Ressourcen
```

System-Prompt-Ergänzung für den Health-KI-Assistenten:
> "Du hast Zugriff auf die komplette Patientenakte via `query_fhir_data`. Antworte auf Deutsch, medizinisch korrekt aber verständlich. Stelle keine Diagnosen — erkläre nur was in der Akte steht. Verweise bei Unsicherheiten auf den behandelnden Arzt."

Der Floating-Button übergibt die aktuelle Kategorie als Kontext:
- Auf Diagnosen-Seite → `resource_types=["Condition"]`
- Auf Laborwerte-Seite → `resource_types=["Observation"]`
- Auf Übersicht → keine Einschränkung (alle Typen)

---

### Frontend

**Struktur** (`frontend/src/features/health/`):

```
features/health/
├── HealthPage.tsx              # Router-Shell, rendert Sidebar + aktive View
├── HealthSidebar.tsx           # Aktenschrank-Navigation mit Sektionen
├── KiFloatingButton.tsx        # Kontextsensitiver KI-Button (rechts unten)
├── views/
│   ├── UebersichtView.tsx      # Kacheln: Diagnosen-Zähler, Medikamente, Laborstatus + Alerts
│   ├── ZeitstrahlView.tsx      # Alle Events chronologisch, filterbar nach Typ
│   ├── DiagnosenView.tsx       # Tabelle: Name, ICD, Seit, Status (aktiv/abgeklungen)
│   ├── MedikamenteView.tsx     # Tabelle: Medikament, Dosis, Verschreiber, Seit
│   ├── LaborwerteView.tsx      # Tabelle + Trendanzeige für Verlaufswerte (HbA1c etc.)
│   ├── AllergienView.tsx
│   ├── ImpfungenView.tsx
│   ├── EingriffeView.tsx
│   ├── ArztbesuecheView.tsx
│   ├── BefundeView.tsx
│   ├── DokumenteView.tsx
│   ├── AppleHealthView.tsx     # bestehend — nur in neue Sidebar integriert
│   ├── SchlafView.tsx          # bestehend — nur in neue Sidebar integriert
│   └── KiAssistentView.tsx     # vollständiger Chat-Tab mit Gesprächshistorie
└── components/
    ├── FhirImportButton.tsx    # Upload-Button mit Drag & Drop
    └── ResourceTable.tsx       # wiederverwendbare sortierbare Tabelle
```

**Sidebar-Sektionen:**
```
PATIENTENAKTE
  🗂 Übersicht
  📅 Zeitstrahl

MEDIZINISCH
  🔴 Diagnosen
  💊 Medikamente
  🧪 Laborwerte
  🤧 Allergien
  💉 Impfungen
  🔪 Eingriffe

KONTAKTE
  🏥 Arztbesuche
  📋 Befunde
  📄 Dokumente

TRACKING
  🍎 Apple Health
  😴 Schlaf

KI
  💬 KI-Assistent
```

**Routing:** `/health/:category` (Deep-Link, Browser-Back funktioniert)

**Import-Flow:**
1. Button "Patientenakte aktualisieren" in Übersicht
2. Datei-Dialog öffnet (akzeptiert `.json`)
3. Upload an `POST /api/health/fhir/import`
4. Toast: "47 Einträge importiert, 12 aktualisiert"

**Migration bestehender Tabs:**
`Übersicht`, `Verlauf` und `Schlaf` werden in die neue Sidebar integriert. Kein Datenverlust, nur neues Layout. `Verlauf` wird zum Zeitstrahl.

---

## Datenschutz

- Jeder API-Endpoint extrahiert `user_id` aus dem JWT und filtert ausschließlich auf diese
- Kein FHIR-JSON landet in Logs oder Fehlerausgaben
- `resource_json` wird nie an andere User-Kontexte weitergegeben
- KI-Tool gibt nur Daten des aktuell authentifizierten Users zurück

---

## Fehlerbehandlung

| Fehlerfall | Verhalten |
|---|---|
| Datei ist kein FHIR Bundle | Toast: "Keine gültige FHIR-Datei" |
| Unbekannte resourceType | Gespeichert, kein Fehler, in UI nicht angezeigt |
| Teilweise fehlgeschlagen | Response zeigt `errors[]` mit Details, erfolgreiche Teile werden trotzdem gespeichert |
| Leere Kategorie | View zeigt "Keine Einträge" statt leerem Zustand |

---

## Tests

- `core/tests/test_fhir_import_smoke.py`
  - Bundle importieren → Ressourcen zählen
  - Zweiten Import (Merge) → keine Duplikate, aktualisierte Felder
  - Falsches Format → klare Fehlermeldung
  - User-Isolation → User B sieht keine Daten von User A

- `core/tests/test_fhir_query_smoke.py`
  - `query_fhir_data` Tool mit realen DB-Einträgen
  - Volltextsuche trifft richtige Ressourcen

---

## Implementierungsphasen

| Phase | Inhalt | Dateien |
|---|---|---|
| 1 | DB-Migration + `db/fhir.py` | `021_fhir_resources.sql`, `db/fhir.py` |
| 2 | Import-API + Tests | `api/routes/fhir.py`, `test_fhir_import_smoke.py` |
| 3 | Agent-Tool + Tests | `tools/fhir_data.py`, `test_fhir_query_smoke.py` |
| 4 | Frontend Sidebar + alle Views | `features/health/` |
| 5 | KI-Tab + Floating Button | `KiAssistentView.tsx`, `KiFloatingButton.tsx` |
