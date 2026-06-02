# Feature Map: Patientenakte — FHIR R4, Gesundheitsdaten, EGA

> **Modul:** `core/src/hydrahive/patientenakte/`  
> **Frontend:** `frontend/src/features/health/`  
> **Was:** Digitale Patientenakte im FHIR R4 Format. Import aus TK-App/EGA. KI-gestützte Analyse.  
> **Warum:** Medizinische Daten sicher lokal speichern und per KI auswertbar machen.

---

## SSOT-Architektur

Nach dem Umbau 2026-05-31 ist `schema.py` die **EINE Wahrheitsquelle** für alle 10 Entitäten.
Frontend zieht Schema per `useAkteSchema()` von `GET /api/akte/_schema` — kein Spiegel mehr.

---

## Entitäten (FHIR-Ressourcen)

| Entität | FHIR-Typ | Beschreibung |
|---|---|---|
| Diagnosen | `Condition` | ICD-Codes, Diagnose-Datum, Arzt |
| Medikamente | `MedicationRequest` | Wirkstoff, Dosis, Verordner |
| Laborwerte | `Observation` | Wert, Einheit, Datum, Referenzbereich |
| Allergien | `AllergyIntolerance` | Allergen, Schweregrad, Reaktion |
| Impfungen | `Immunization` | Impfstoff, Datum, Charge |
| Eingriffe | `Procedure` | OP, Behandlung, Datum, Ort |
| Arztbesuche | `Encounter` | Datum, Arzt, Fachgebiet, Notizen |
| Befunde | `DiagnosticReport` | Bericht-Text, Datum, Arzt |
| Dokumente | `DocumentReference` | Dateien (PDF, Bilder), Kategorie |
| Patient | `Patient` | Stammdaten, Geburtsdatum, Adresse |

---

## Dateien

### Backend
| Datei | Verantwortung |
|---|---|
| `patientenakte/schema.py` | **SSOT**: Registry aller Entitäten mit Feldern, Types, Validierung |
| `api/routes/patientenakte.py` | CRUD-Endpoints für alle Entitäten, `GET /api/akte/_schema` |
| `api/routes/fhir.py` | FHIR R4 REST-API (Standard-konform) |
| `api/routes/ega.py` | EGA-Import-Endpoint |
| `db/fhir.py` | FHIR-Daten in SQLite (JSON-Blobs) |
| `db/ega.py` | EGA-Import-Tracking |
| `tools/fhir_data.py` | `query_fhir_data` Tool für Agents |

### Frontend
| Datei | Verantwortung |
|---|---|
| `health/HealthPage.tsx` | Haupt-Seite mit Sidebar-Navigation |
| `health/HealthSidebar.tsx` | Navigation durch Entitäten |
| `health/components/ResourceTable.tsx` | Generische Tabelle (via Schema) |
| `health/components/AkteEntryModal.tsx` | Eintrag anlegen/bearbeiten |
| `health/components/FhirImportButton.tsx` | FHIR-Datei importieren |
| `health/components/EgaImportButton.tsx` | EGA-Export importieren |
| `health/_HealthBuddyBox.tsx` | KI-Analyse-Box im Health-Tab |
| `health/_AppleHealthView.tsx` | Apple Health Daten-Ansicht |
| `health/_SchlafView.tsx` | Schlaf-Statistiken |
| `health/_SleepChart.tsx` | Schlaf-Diagramm |
| `health/KiFloatingButton.tsx` | Floating KI-Analyse-Button |

---

## Import-Quellen

1. **TK-App (Techniker Krankenkasse)** — FHIR R4 Export
2. **EGA (Elektronische Gesundheitsakte)** — Standard-Export
3. **Manuell** — Direkteingabe über Web-UI
4. **Agent** — Via `query_fhir_data` Tool + manuelle Eingabe durch Agent

---

## query_fhir_data Tool

```python
query_fhir_data(
    resource_types=["Condition", "MedicationRequest"],  # Optional: Filtern
    search_text="HbA1c"  # Optional: Volltextsuche im JSON
)
→ FHIR-Ressourcen als strukturierter Text
```

**Wichtig:** Agent stellt **keine Diagnosen** — erklärt nur was in der Akte steht.
Bei medizinischen Unsicherheiten: Verweis auf Arzt.

---

## Akte-Dokumente (Phase 3a — feat/akte-dokumente)

Branch `origin/feat/akte-dokumente` hat bereits:
- `documents.py` — Datei-Storage (save/open/delete), size+ext-Guard, 0600-Permissions
- `pypdf` für PDF-Verarbeitung
- Schema-Eintrag für `DocumentReference`

Issues #167/#168/#169 für Phase 3a (Dokumente), #170-#173 für Phase 3b (FTS5).

---

## Apple Health

Zusätzlich zur FHIR-Akte: Apple Health Daten via separatem Import:
- `db/health.py` — Metriken-Speicher
- `tools/health_data.py` — `query_health_data` Tool
- `health/_AppleHealthView.tsx` — UI
- Metriken: step_count, heart_rate, sleep_analysis, active_energy, ...

---

## Verwandte Subsysteme

- **→ DB** (`03-db.md`): `fhir`, `health`, `ega` Tabellen
- **→ Tools** (`02-tools.md`): `query_fhir_data`, `query_health_data`
- **→ API** (`04-api.md`): `routes/patientenakte.py`, `routes/fhir.py`
