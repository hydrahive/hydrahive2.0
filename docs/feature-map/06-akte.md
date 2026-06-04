# Patientenakte & Health

> ⚠️ **Ausgelagert (2026-06, Etappen 1–3): die gesamte Patientenakte + FHIR/eGA-Import +
> Apple-Health ist in das installierbare Modul `patientenakte` gewandert.** Code liegt jetzt
> unter `modules/patientenakte/{backend,frontend,migrations}`, API unter
> `/api/modules/patientenakte/{akte,fhir,ega,health-data}/*`, Buddy-Box läuft über den
> Modul-Widget-Slot. Core behält nur: Migrationen 015/016/020/021/022/023 (Tabellen-DDL +
> Daten, unbeweglich), die 2 Health-Settings (`health_api_key`, `health_ingest_user`) und den
> `/api/health`-Versionscheck (anderer Endpunkt). Die `core/`-Pfade unten sind **historisch
> (Pre-Port)** — der lebende Code ist im Modul. Siehe Memory `project_akte_module_port`.

> Stand: 2026-06-02. Subsystem-Scope: strukturierte schreibbare Patientenakte (ePA-light),
> read-only eGA/FHIR-Importschicht (Kassendaten), Apple-Health-Ingest, Zahnfee-Nacht-Briefing
> und der gesamte Frontend-`features/health/`-Bereich.
> SPEC-Referenz: SPEC.md:900–940 (Patientenakte), SPEC.md:750–757 (Zahnfee).

Das Subsystem besteht aus **vier voneinander getrennten Datenschichten**, die im Frontend unter
einer gemeinsamen Sidebar zusammenlaufen:

1. **Patientenakte (ePA-light)** — eigene relationale SQLite-Domäne (`akte_*`-Tabellen),
   schreibbar via REST + KI, Single-User ("jeder User eine Akte"). SSOT = `schema.py`-Registry.
2. **FHIR-Blob-Store** — read-only `fhir_resources`-Tabelle, importierte FHIR-R4-Bundles.
3. **eGA-Blob-Store** — read-only `ega_records`-Tabelle, native TK-eGA-Records (Kassendaten).
4. **Apple-Health-Ingest** — `health_ingest` (Roh-Payloads) + `health_daily` (Tages-Rollup).

Plus die **Zahnfee** (nächtliches Datamining-Briefing) — technisch im Health-Bereich verortet,
aber datenmäßig vom Akten-Stack unabhängig (liest Datamining-Mirror, schreibt eine JSON-Datei).

---

## WAS

### A. Patientenakte — Backend-Module

- `patientenakte/schema.py` — **Registry-SSOT**: `ENTITIES`-dict mit 9 `EntitySpec`-Einträgen,
  `FieldSpec`/`EntitySpec`-Dataclasses, `ui_schema()`-Serialisierer, `_f()`-Field-Helper,
  `COMMON_FIELDS`-Konstante.
- `patientenakte/entities.py` — generischer registry-getriebener CRUD über alle 9 Entitäten:
  `create`, `batch_create`, `list_for`, `get`, `update`, `delete`, plus interne Helfer
  `_spec`, `_ensure_owner`, `_split`, `_sort_date_for`, `_insert`, `_update`, `_upsert`, `_row_to_dict`.
- `patientenakte/patients.py` — Patient-Stammdaten-CRUD mit Owner-Isolation:
  `create`, `get`, `list_for`, `get_own_id`, `update`, `delete`, `_row_to_patient`.
- `patientenakte/views.py` — aggregierte Sichten: `summary` (Count je Entität),
  `timeline` (chronologischer Cross-Entity-Zeitstrahl).
- `patientenakte/_dates.py` — `to_sort_date()`: Best-Effort-Extraktion eines sortierbaren
  ISO-Datums aus Freitext via Regex `_ISO`.
- `patientenakte/models.py` — `Patient`-TypedDict (nur Typ, keine Logik).
- `patientenakte/import_proto.py` — YAML/CSV-Prototyp-Importer: `import_akte`,
  `_load_yaml`, `_find_patient`, `_import_labor_csv`; CLI-Entrypoint `__main__`.
- `patientenakte/__init__.py` — Re-Export `ENTITIES`, `EntitySpec`, `COMMON_FIELDS`.

### B. Patientenakte — die 9 Entitäten (Registry-Keys)

Jede mit API-Key, SQL-Tabelle, UI-Label, getypten Feldern, label_fields, list_columns,
date_field, array_fields, numeric_fields:

1. `conditions` → `akte_condition` „Diagnosen" — Felder: diagnose(*), icd_code, status(select:
   aktuell/chronisch/ausgeheilt/verdacht), diagnostiziert_am(date), arzt, koerperstelle,
   erstmanifestation, bemerkungen(textarea). date_field=diagnostiziert_am.
2. `medications` → `akte_medication` „Medikamente" — name(*), wirkstoff, atc_code, klasse,
   dosierung, beginn(date), ende(date), arzt, zweck, status(select: aktuell/historisch/entlassung),
   letzte_verordnung(date). date_field=beginn. array_fields=(nebenwirkungen).
3. `observations` → `akte_observation` „Laborwerte" — parameter(*), wert(number), wert_text,
   einheit, referenz_min(number), referenz_max(number), flag(select: normal/high/low),
   datum(date), labor, material. date_field=datum. numeric_fields=(wert, referenz_min, referenz_max).
4. `events` → `akte_encounter` „Ereignisse" — typ(*), datum_von(date), datum_bis(date),
   einrichtung, fachabteilung, fallnummer, hauptdiagnose, verlauf(textarea). date_field=datum_von.
   array_fields=(nebendiagnosen, prozeduren, op_codes, entlassmedikation).
5. `imaging` → `akte_imaging` „Bildgebung" — modalitaet(*), datum(date), region, einrichtung,
   ueberweiser, serien_beschreibung, anzahl_bilder, dicom_pfad, befund(textarea).
   date_field=datum. array_fields=(vorschau_bilder).
6. `allergies` → `akte_allergy` „Allergien" — substanz(*), reaktion, schweregrad(select:
   leicht/mittel/schwer), festgestellt_am(date). date_field=festgestellt_am.
7. `practitioners` → `akte_practitioner` „Ärzte" — name(*), fach, einrichtung, adresse, telefon,
   rolle(select: hausarzt/facharzt/sonstige). **kein date_field** (taucht nicht in Timeline auf).
8. `documents` → `akte_document` „Dokumente" — titel(*), typ, datum(date), datei_pfad, mime_type,
   ocr_text(textarea). date_field=datum. array_fields=(verknuepfte_entitaeten).
9. `notes` → `akte_note` „Notizen" — titel(*), inhalt(textarea), kategorie, datum(date).
   date_field=datum.

`COMMON_FIELDS` = `("external_id", "quelle", "confidence", "verifiziert")` — auf jeder Entität
zusätzlich vorhanden (in jeder `akte_*`-Tabelle als Spalte).

### C. Patientenakte — REST-Endpoints (`api/routes/patientenakte.py`, prefix `/api/modules/patientenakte/akte`)

- `GET  /api/modules/patientenakte/akte` — eigene Akte + `counts` (404 wenn keine).
- `POST /api/modules/patientenakte/akte` — eigene Akte anlegen (409 wenn existiert).
- `PATCH /api/modules/patientenakte/akte` — Stammdaten der eigenen Akte aktualisieren.
- `GET  /api/modules/patientenakte/akte/_schema` — UI-Registry (SSOT) als JSON. Keine Akte nötig.
- `GET  /api/modules/patientenakte/akte/timeline` — Cross-Entity-Zeitstrahl.
- `GET  /api/modules/patientenakte/akte/summary` — Counts je Entität.
- `GET  /api/modules/patientenakte/akte/{entity}` — Liste (Query: `q`, `status`).
- `POST /api/modules/patientenakte/akte/{entity}` — Eintrag anlegen (Upsert via external_id).
- `POST /api/modules/patientenakte/akte/{entity}/batch` — Batch-Import (`{items:[…]}`).
- `GET  /api/modules/patientenakte/akte/{entity}/{eid}` — einzelner Eintrag.
- `PATCH /api/modules/patientenakte/akte/{entity}/{eid}` — Eintrag aktualisieren.
- `DELETE /api/modules/patientenakte/akte/{entity}/{eid}` — Eintrag löschen.
- Alle hinter `require_auth` (Token/JWT). `_entity_or_404`-Guard für unbekannte Entitäten.

### D. FHIR — Endpoints (`api/routes/fhir.py`, prefix `/api/modules/patientenakte/fhir`)

- `POST /api/modules/patientenakte/fhir/import` — FHIR-Bundle importieren (Upsert, 422 bei invalid).
- `POST /api/modules/patientenakte/fhir/import-ega` — TK-eGA-ZIP hochladen → intern zu FHIR konvertiert → importiert.
- `GET  /api/modules/patientenakte/fhir/resources/{resource_type}` — alle Ressourcen eines Typs.
- `GET  /api/modules/patientenakte/fhir/summary` — Count je resourceType.
- `GET  /api/modules/patientenakte/fhir/timeline` — alle Ressourcen chronologisch (nach imported_at), gebounded auf 1000.
- Alle hinter `require_auth`.

### E. eGA — Endpoints (`api/routes/ega.py`, prefix `/api/modules/patientenakte/ega`)

- `POST /api/modules/patientenakte/ega/import` — TK-eGA-Export-ZIP nativ importieren (ohne FHIR-Konvertierung).
- `GET  /api/modules/patientenakte/ega/summary` — Count je dto_type.
- `GET  /api/modules/patientenakte/ega/records/{dto_type}` — alle Records eines DTO-Typs.
- `GET  /api/modules/patientenakte/ega/costs` — Kostenzusammenfassung (ambulant_eur, medikamente_eur, medikamente_zuzahlung_eur).
- `GET  /api/modules/patientenakte/ega/timeline` — chronologische Liste (gebounded auf 200).
- Alle hinter `require_auth`.

### F. Apple-Health — Endpoints (`api/routes/health_data.py`, prefix `/api/modules/patientenakte/health-data`)

- `POST /api/modules/patientenakte/health-data/ingest` — **kein require_auth**; Key-basiert (Header `X-HH-Health-Key`,
  `Authorization: Bearer`, oder `?key=`-Query [deprecated #207]). Rate-Limited je Client-IP.
- `GET  /api/modules/patientenakte/health-data/data` — letzte N Ingest-Records (Query: `limit` 1–500, `automation_id`). require_auth.
- `GET  /api/modules/patientenakte/health-data/metrics` — Tages-Rollup-Zusammenfassung (Query: `days` 1–365, `metric`). require_auth.
- `GET  /api/modules/patientenakte/health-data/data/{record_id}` — Roh-Payload eines Records. require_auth.

### G. Zahnfee — Endpoints (`api/routes/zahnfee.py`, prefix `/api/zahnfee`)

- `GET  /api/zahnfee/briefing` — letztes Briefing (require_auth).
- `GET  /api/zahnfee/config` — Konfiguration (**require_admin**).
- `PUT  /api/zahnfee/config` — Konfiguration setzen (require_admin, Pydantic-`ConfigBody`).
- `POST /api/zahnfee/run` — manuell triggern, wartet auf Runner (require_admin).

### H. KI-Tools (Agenten-Tools, `tools/`)

- `query_fhir_data` (`tools/fhir_data.py`) — liest FHIR-Akte; Args `resource_types[]`, `search_text`.
  Formatiert FHIR-Ressourcen in lesbaren Text (`_format_resource`). category=personal. Bindet an
  `ctx.user_id`. Limit 100 Ressourcen pro Antwort.
- `query_health_data` (`tools/health_data.py`) — liest Apple-Health-Tagesmetriken;
  Args `days` (1–365), `metric`. Setzt `settings.health_api_key` voraus; bindet an `ctx.user_id`.
  category=personal.
- Beide registriert in `tools/__init__.py:_build_registry` (`fhir_data.TOOL`, `health_data.TOOL`).
- **Es gibt KEIN Patientenakte-Schreibtool** — der Akten-CRUD ist nur via REST erreichbar, nicht
  als Agenten-Tool. (FHIR/Health sind read-only Tools.)

### I. Config-Flags / Env-Vars

- `HH_HEALTH_API_KEY` → `settings.health_api_key` (leer ⇒ Ingest-Endpoint 403, FHIR-Tool egal,
  Health-Tool fail). `_services.py:128`.
- `HH_HEALTH_INGEST_USER` → `settings.health_ingest_user` (Default `"till"`). `_services.py:133`.
- Zahnfee-Config-Datei `HH_CONFIG_DIR/zahnfee.json` mit Feldern: enabled, model, run_hour (0–23),
  lookback_hours (1–720), source_datamining, source_mail, soul.
- Zahnfee-Briefing-Datei `HH_DATA_DIR/zahnfee_briefing.json`.

### J. Frontend — `features/health/`

**Live (in `HealthPage.tsx` verdrahtet):**

- `HealthPage.tsx` — Layout + React-Router-Routes + `ImportView` (Platzhalter-Stub).
- `HealthSidebar.tsx` — 4 Sektionen (Akte / Import / Tracking / KI), 15 NavLinks.
- `KiFloatingButton.tsx` — Floating-Button → `/health/ki`.
- `useAkteSchema.ts` — modul-globaler Cache + Promise-Dedup für `GET .../_schema`.
- `api.ts` — `healthApi`, `egaApi`, `fhirApi`, `researchApi`, `akteApi` + alle TS-Interfaces +
  `toAkteRecord`-Adapter.
- `components/AkteErrorBoundary.tsx` — Render-Error-Boundary je View (resetKey=pathname).
- `components/AkteEntryModal.tsx` — generisches Formular-Modal (schema-getrieben, create/edit).
- `components/ResourceTable.tsx` — generische Tabelle mit EmptyState.
- `components/VerifyBadge.tsx` — Verifiziert-Punkt (grün=verifiziert, orange=klickbar).
- `views/AkteDashboard.tsx` — Übersicht (`uebersicht`): Stammdaten-Header + Anlegen-Formular +
  Count-Kacheln + „rote Fakten" (aktive Diagnosen / Allergien / Dauermedikation).
- `views/AkteTimeline.tsx` — Zeitstrahl (`timeline`): Filter je Entität, Verify inline.
- `views/AkteEntityList.tsx` — generische Listenansicht (`conditions`/`medications`/`allergies`/
  `events`/`imaging`/`practitioners`/`documents`/`notes`): Suche, Verify, Edit, Delete, + Neu.
- `views/AkteLabCharts.tsx` — Laborwerte (`observations`): Recharts-Trend je Parameter mit
  Referenzbereichen (hardcoded `REFERENCE_RANGES`).
- `_AppleHealthView.tsx` (`AppleHealthView`) — Apple-Health-Trends (`apple` UND `ki`).
- `_SchlafView.tsx` (`SchlafView`) — Schlaf-Tracking (`schlaf`).
- `_TrendChart.tsx` (`TrendChart`) — Recharts-LineChart + `METRIC_LABELS` (40+ Metrik-Übersetzungen).
- `_SleepChart.tsx` (`SleepChart`) — Recharts-BarChart, 7h-Referenzlinie.

**Routen-Mapping (`HealthPage.tsx`):** `uebersicht`→AkteDashboard, `timeline`→AkteTimeline,
`conditions/medications/allergies/events/imaging/practitioners/documents/notes`→AkteEntityList,
`observations`→AkteLabCharts, `import`→ImportView (Stub), `apple`→AppleHealthView,
`schlaf`→SchlafView, **`ki`→AppleHealthView** (Fehlverdrahtung, siehe Offene Enden).

**Tot / nicht in HealthPage referenziert (0 externe Referenzen):**
`views/UebersichtView.tsx`, `views/DiagnosenView.tsx`, `views/LaborwerteView.tsx`,
`views/MedikamenteView.tsx`, `views/ArztabrechnungView.tsx`, `views/ResearchApisView.tsx`,
`views/SimpleListView.tsx`, `views/KiAssistentView.tsx`, `views/ZeitstrahlView.tsx`.
`components/EgaImportButton.tsx` + `components/FhirImportButton.tsx` (nur vom toten UebersichtView
benutzt). `_HealthBuddyBox.tsx` (nur von `features/buddy/BuddyPage.tsx` referenziert — lebt außerhalb).

---

## WIE

### Patientenakte — Schreibpfad (Klick → DB)

1. UI: „+ Neu" in `AkteEntityList` öffnet `AkteEntryModal` mit `ui_fields` aus dem Schema.
2. `AkteEntryModal.handleSubmit`: sammelt nur ausgefüllte Felder, castet `type==="number"` zu
   `Number()`, prüft das erste `required`-Feld clientseitig, ruft
   `akteApi.createEntity(entity, payload)` (oder `updateEntity` bei `existing`).
3. `akteApi.createEntity` → `POST /api/modules/patientenakte/akte/{entity}` mit JSON-Body.
4. Route `create_my_entity`: `patients.get_own_id(user)` löst die eigene Akte auf (404 wenn keine),
   `_entity_or_404(entity)`, dann `entities.create(user, pid, entity, data)`.
5. `entities.create`: `_spec(entity)` holt den `EntitySpec`, `_ensure_owner` prüft Besitz
   (via `patients.get`), öffnet `db(immediate=True)`-Transaktion (BEGIN IMMEDIATE), ruft `_upsert`.
6. `_upsert`: `_split` trennt getypte Felder (`spec.fields`) von array_fields (→ `extra_json`) und
   COMMON_FIELDS; castet `verifiziert` zu int(bool). Wenn `external_id` vorhanden: SELECT auf
   `(patient_id, external_id)` → existiert → `_update`, sonst `_insert`.
7. `_insert`: generiert `uuid7()`, baut INSERT mit festen Spalten (id, patient_id, created_at,
   updated_at, extra_json, sort_date) + getypte Spalten. `sort_date` aus `_sort_date_for`
   (`to_sort_date(data[date_field])`).
8. SQLite committet beim Verlassen des `with db()`-Blocks.

### Patientenakte — Lesepfad (List)

1. `akteApi.listEntity(entity, {q,status}, labelFields)` → `GET …/{entity}?q=&status=`.
2. Route `list_my_entity` → `entities.list_for`: SELECT `*` WHERE patient_id, optionaler
   `status`-Filter (nur wenn „status" ein Feld der Entität ist), optionaler `q`-LIKE über **alle**
   `spec.fields`. ORDER BY `sort_date DESC NULLS LAST, created_at DESC`.
3. `_row_to_dict`: alle Spalten außer `extra_json`; `extra_json` wird geparst und ins flache Dict
   gemerged.
4. Frontend-Adapter `toAkteRecord(row, labelFields)`: leitet `label` aus dem ersten gefüllten
   `label_field` ab (sonst `—`), packt die flache Row in `record`, hebt `id`/`external_id`/
   `sort_date`/`verifiziert` nach oben.

### Patientenakte — Timeline / Summary

- `views.summary`: iteriert `ENTITIES`, `SELECT COUNT(*)` je Tabelle WHERE patient_id.
- `views.timeline`: iteriert `ENTITIES`, `SELECT *` WHERE patient_id AND `sort_date IS NOT NULL`,
  baut Einträge `{entity, label, sort_date, record}`, sortiert global nach `sort_date` absteigend.
  → `practitioners` (kein date_field, also nie sort_date) erscheinen **nie** in der Timeline.

### Schema-SSOT-Fluss (Frontend rendert generisch)

1. `GET …/_schema` → `ui_schema()` serialisiert `ENTITIES` zu `{entities:{key:{label, label_fields,
   list_columns, date_field, numeric_fields, ui_fields:[…]}}}`.
2. `useAkteSchema()` cached das Resultat modul-global (eine Anfrage pro Page-Load, Promise-Dedup).
3. `AkteEntityList` baut Spalten generisch: labelCol (erstes label_field) + dataCols (list_columns)
   + dateCol + actionCol. `AkteEntryModal` rendert Felder generisch nach `type`
   (text/number/date/textarea/select).
   → kein handgespiegeltes `akteFields.ts`/`ENTITY_COLUMNS` mehr (war früher Drift-Quelle).

### eGA-Import-Fluss

1. UI lädt ZIP → `POST /api/modules/patientenakte/ega/import` (`egaApi.importZip` via FormData).
2. `ega.py:import_ega`: `extract_ega_records(data)` (`fhir_ega.py`) öffnet ZIP in-memory,
   lädt alle `.json`, sammelt DTO-Listen, mappt auf `(dto_type, record)`-Tupel.
   DTO→Typ-Mapping: EncounterDTO→Encounter, HospitalClaimDTO→HospitalStay,
   MedicationDispenseDTO→MedicationDispense, AmbulantClaimDTO→AmbulantClaim,
   MedicationClaimDTO→MedicationClaim, ProcedureDTO→Procedure; ConditionDTO→innere `contained`
   ICD-Conditions (dedupliziert per `code|display`).
3. `ega_db.upsert_records`: je Record `_stable_id` (TK-id mit dto-Präfix, sonst SHA256 über
   businessObjectId/JSON), `_display` (typ-spezifischer Anzeigetext), `_sort_date`
   (metaInformation.sortDate / period.start / billablePeriod.start). Upsert per `(id, user_id)`.
   Statistik `{imported, updated, errors}` zurück.

### FHIR-Import-Fluss

1. UI lädt `.json`-Bundle (`fhirApi.importBundle` liest Text, `JSON.parse`, `POST /api/modules/patientenakte/fhir/import`)
   oder `.zip` (`fhirApi.importEgaZip` → `POST /api/modules/patientenakte/fhir/import-ega`).
2. `fhir.py:import_bundle`/`import_ega_zip`: ZIP-Pfad ruft `convert_ega_zip(data)` (`fhir_ega.py`) —
   konvertiert dieselben DTOs in echte FHIR-R4-Ressourcen (`_encounters`, `_conditions`,
   `_medication_dispenses`, `_procedures`, `_hospital_encounters`), baut ein collection-Bundle.
3. `fhir_db.upsert_bundle`: prüft `resourceType=="Bundle"`, iteriert `entry[].resource`, Upsert per
   `(user_id, resource_type, resource_id)`. Fehlende type/id → `errors++`.

### Apple-Health-Ingest-Fluss (kritischster Sicherheitspfad)

1. iPhone-Automation (Apple Health Auto Export) `POST /api/modules/patientenakte/health-data/ingest` mit Payload +
   Headern (automation-name/-id, session-id, automation-period/-aggregation) + Health-Key.
2. `check_rate(f"health-ingest:{client_ip}")` (Sliding-Window-Limiter); 429 + Retry-After bei Limit.
3. `_check_key`: `settings.health_api_key` leer → **403** `health_ingest_disabled`. Sonst
   `verify_secret` (konstant-zeitig, `hmac.compare_digest`) gegen Header / Bearer / `?key=`.
   Kein Treffer → **401** `bad_key`. Query-Key löst Warn-Log aus (#207).
4. **user_id kommt NICHT aus dem Request** — `user = settings.health_ingest_user`. Der Key bindet an
   genau einen User (Single-Device-Ingest) → kein Cross-User-PHI-Schreiben.
5. `health_db.insert`: `uuid7()`-Record-ID, INSERT in `health_ingest` + `_process_payload_to_daily`
   in **derselben** Transaktion (`db()`-Block). Schlägt der Rollup fehl → Rohsatz rollt zurück.
6. `_process_payload_to_daily`: extrahiert `data.metrics[]`, gruppiert Samples je
   `(metric_name, date[:10])`, aggregiert via `_aggregate_samples` (Summe für `_CUMULATIVE` ∪
   `_TIME_BASED`, sonst Durchschnitt), `INSERT … ON CONFLICT(date, metric_name, user_id) DO UPDATE`
   (kumulative/zeitbasierte addieren, sonst Mittelwert (alt+neu)/2).
7. Antwort `{id, metrics:len, workouts:len}` (workouts werden gezählt, **aber nicht gerollt** — siehe
   Offene Enden).

### Apple-Health-Metrics-Lesepfad

- `health_db.get_metrics_summary(user_id, days, metric?)`: `since_date = heute - days`, SELECT aus
  `health_daily` ab `since_date`, gruppiert je Metrik, berechnet `latest`, `trend` (%-Differenz zum
  Durchschnitt der Vortage), `unit`, `days[]`. `last_ingest` aus `health_ingest`.
- Frontend `AppleHealthView`/`SchlafView` → `healthApi.metrics(days)` → Recharts.

### Zahnfee-Fluss (Nacht-Batch)

1. `scheduler.run_loop` (Lifespan-Task `lifespan.py:129`): wartet 30 s nach Start, prüft jede Minute.
2. Wenn `cfg.enabled` UND `now.hour == cfg.run_hour` UND noch nicht heute gelaufen UND kein heutiges
   Briefing existiert → `asyncio.create_task(runner.run())`. Zusätzlich (nur wenn `cfg.model` gesetzt):
   `cards.consolidate.consolidate_recent` (Proaktiver-Recall-L2, reuse des Tages-Ticks).
3. `runner.run`: lädt Config, holt Events via `_fetch_events` (direkt aus Datamining-Mirror-DB,
   `mirror_query.search_events`, letzte `lookback_hours`), formatiert (`_format_events`), baut
   System+User-Prompt, ruft `llm.client.complete` (temperature 0.3, max_tokens 2048),
   `_extract_json` (5-stufige robuste Extraktion), baut `storage.Briefing`, `storage.save`.
4. Bei Fehler: leeres Briefing mit `error`-Feld. Frontend liest via `/api/zahnfee/briefing` (lebt im
   Buddy-/Dashboard-Bereich, nicht in `features/health/`).

### KI-Tool-Fluss (Agent fragt Akte)

- Agent ruft `query_fhir_data` (Args resource_types/search_text) → `fhir_db.query_fulltext` /
  `query_by_type` / `timeline` → `_format_resource` formatiert je Ressource → max 100 Zeilen.
- Agent ruft `query_health_data` (Args days/metric) → `health_db.get_metrics_summary` → aggregierte
  Metriken oder „Keine Health-Daten"-Hinweis.

---

## WO

### Patientenakte — Backend

- `core/src/hydrahive/patientenakte/schema.py:21` — `FieldSpec`-Dataclass.
- `…/schema.py:32` — `EntitySpec`-Dataclass; `:44` `fields`-Property.
- `…/schema.py:50` — `COMMON_FIELDS`.
- `…/schema.py:53` — `ui_schema()`.
- `…/schema.py:85` — `_f()`-Helper.
- `…/schema.py:90` — `ENTITIES`-dict (die 9 Specs, Zeilen 91–224).
- `…/entities.py:24` `_spec`, `:30` `_ensure_owner`, `:35` `_split`, `:46` `_sort_date_for`,
  `:50` `_insert`, `:64` `_update`, `:82` `_upsert`, `:96` `_row_to_dict`.
- `…/entities.py:103` `create`, `:110` `batch_create`, `:119` `list_for`, `:138` `get`,
  `:147` `update`, `:155` `delete`.
- `…/patients.py:10` `_JSON_FIELDS`, `:12` `_SCALAR`, `:16` `create`, `:35` `_row_to_patient`,
  `:43` `get`, `:51` `list_for`, `:59` `get_own_id`, `:68` `update`, `:85` `delete`.
- `…/views.py:12` `summary`, `:24` `timeline`.
- `…/_dates.py:10` `_ISO`-Regex, `:13` `to_sort_date`.
- `…/import_proto.py:36` `import_akte`, `:152` `_import_labor_csv`, `:170` CLI `__main__`.
- `…/models.py:7` `Patient`-TypedDict.

### Patientenakte — Route

- `core/src/hydrahive/api/routes/patientenakte.py:19` Router (prefix `/api/modules/patientenakte/akte`).
- `:24` `_entity_or_404`. `:39` GET root, `:52` POST root, `:61` PATCH root.
- `:72` `/_schema`, `:82` `/timeline`, `:91` `/summary`.
- `:105` GET `{entity}`, `:116` POST `{entity}`, `:126` POST `{entity}/batch`,
  `:136` GET `{entity}/{eid}`, `:149` PATCH `{entity}/{eid}`, `:159` DELETE `{entity}/{eid}`.

### FHIR / eGA — Backend

- `core/src/hydrahive/api/routes/fhir.py:14` Router; `:17` import, `:33` import-ega,
  `:54` resources, `:65` summary, `:74` timeline.
- `core/src/hydrahive/db/fhir.py:13` `RESOURCE_LABELS`, `:28` `upsert_bundle`, `:71` `query_by_type`,
  `:81` `summary`, `:91` `timeline`, `:109` `query_fulltext`.
- `core/src/hydrahive/api/routes/ega.py:14` Router; `:17` import, `:35` summary, `:43` records,
  `:53` costs, `:61` timeline.
- `core/src/hydrahive/db/ega.py:13` `_stable_id`, `:22` `_sort_date`, `:31` `_display`,
  `:68` `upsert_records`, `:100` `summary`, `:109` `query_by_type`, `:118` `cost_summary`,
  `:156` `timeline`.
- `core/src/hydrahive/fhir_ega.py:13` `extract_ega_records`, `:55` `convert_ega_zip`,
  `:78` `_load_zip`, `:97` `_stable_id`, `:104` `_sort_date`, `:113` `_encounters`,
  `:134` `_conditions`, `:172` `_medication_dispenses`, `:200` `_procedures`,
  `:221` `_hospital_encounters`.

### Apple-Health — Backend

- `core/src/hydrahive/api/routes/health_data.py:17` Router; `:20` `_check_key`, `:37` ingest,
  `:89` data-list, `:100` metrics, `:110` get-record.
- `core/src/hydrahive/db/health.py:15` `insert`, `:40` `list_recent`, `:66` `get_payload`,
  `:78` `_CUMULATIVE`, `:84` `_TIME_BASED`, `:87` `_aggregate_samples`,
  `:96` `_process_payload_to_daily`, `:151` `backfill_daily`, `:175` `get_metrics_summary`.
- Ingest-Middleware: `api/middleware/secret_compare.py:13` `verify_secret`,
  `api/middleware/inbound_ratelimit.py:21` `check_rate`, `api/middleware/client_ip.py:14` `client_ip`.

### Zahnfee

- `core/src/hydrahive/zahnfee/config.py:13` `DEFAULT_SOUL`, `:35` `ZahnfeeConfig`, `:46` `_config_path`,
  `:50` `load`, `:66` `save`.
- `…/zahnfee/runner.py:15` `_fetch_events`, `:34` `_extract_json`, `:94` `_format_events`, `:112` `run`.
- `…/zahnfee/scheduler.py:11` `run_loop`.
- `…/zahnfee/storage.py:16` `Briefing`, `:26` `_path`, `:30` `load`, `:42` `save`,
  `:48` `today_str`, `:52` `now_iso`.
- `core/src/hydrahive/api/routes/zahnfee.py:15` Router; `:21` briefing, `:29` get-config,
  `:34` `ConfigBody`, `:44` put-config, `:53` manual-run.

### Tools

- `core/src/hydrahive/tools/fhir_data.py:40` `_format_resource`, `:85` `_execute`, `:119` `TOOL`.
- `core/src/hydrahive/tools/health_data.py:32` `_execute`, `:57` `TOOL`.
- `core/src/hydrahive/tools/__init__.py:59-60` Registrierung.

### Settings / Wiring

- `core/src/hydrahive/settings/_services.py:128` `health_api_key`, `:133` `health_ingest_user`.
- `core/src/hydrahive/api/main.py:132` patientenakte_router, `:151` health_data_router,
  `:152` fhir_router, `:153` ega_router, `:148` zahnfee_router.
- `core/src/hydrahive/api/lifespan.py:128-129` Zahnfee-Scheduler-Task, `:219`/`:225` Shutdown.

### Migrationen

- `…/db/migrations/015_health_ingest.sql` — `health_ingest` (ohne user_id, vor 020).
- `…/db/migrations/016_health_daily.sql` — `health_daily` (PK date,metric_name, vor 020).
- `…/db/migrations/020_health_user_id.sql` — fügt user_id zu beiden hinzu, baut `health_daily`
  mit PK (date, metric_name, user_id) neu, Bestandsdaten → `'till'`.
- `…/db/migrations/021_fhir_resources.sql` — `fhir_resources`.
- `…/db/migrations/022_ega_records.sql` — `ega_records`.
- `…/db/migrations/023_patientenakte.sql` — `akte_patient` + 9 `akte_*`-Entitätstabellen.

### Frontend

- `frontend/src/features/health/HealthPage.tsx:16` `ImportView`-Stub, `:32` `HealthPage`,
  `:51-75` Routes.
- `frontend/src/features/health/HealthSidebar.tsx:7` `SECTIONS`.
- `frontend/src/features/health/api.ts:35` `healthApi`, `:77` `egaApi`, `:126` `fhirApi`,
  `:170` `researchApi`, `:242` `toAkteRecord`, `:255` `akteApi`.
- `frontend/src/features/health/useAkteSchema.ts:7` `useAkteSchema`.
- `frontend/src/features/health/views/AkteDashboard.tsx:8` `calcAge`, `:22` `AkteDashboard`.
- `frontend/src/features/health/views/AkteEntityList.tsx:20` `AkteEntityList`.
- `frontend/src/features/health/views/AkteTimeline.tsx:8` `ENTITY_ICONS`, `:22` `AkteTimeline`.
- `frontend/src/features/health/views/AkteLabCharts.tsx:23` `REFERENCE_RANGES`, `:65` `AkteLabCharts`.
- `frontend/src/features/health/components/AkteEntryModal.tsx:15` `initialForm`, `:24` `AkteEntryModal`.
- `frontend/src/features/health/components/ResourceTable.tsx:18` `ResourceTable`.
- `frontend/src/features/health/components/VerifyBadge.tsx:8` `VerifyBadge`.
- `frontend/src/features/health/components/AkteErrorBoundary.tsx:17` `AkteErrorBoundary`.
- `frontend/src/features/health/_TrendChart.tsx:8` `METRIC_LABELS`, `:52` `TrendChart`.
- `frontend/src/features/health/_SleepChart.tsx:7` `RECOMMENDED_SLEEP_MIN`, `:34` `SleepChart`.
- `frontend/src/features/health/KiFloatingButton.tsx:5` `ROUTE_TO_LABEL`, `:16` `ROUTE_TO_RESOURCE_TYPE`,
  `:27` `KiFloatingButton`.

### Tests

- `core/tests/test_akte_schema.py` — Guard-Tests (Registry⊆Tabelle, label/list/numeric ⊆ fields,
  Lastenheft-Key-Set, select-Options, required-Felder, UI-Field-Typen).
- `core/tests/test_akte_entities.py`, `test_akte_patients.py`, `test_akte_views.py`,
  `test_akte_api.py`, `test_akte_single_user.py`, `test_akte_import.py`,
  `test_akte_schema_endpoint.py`, `test_ega.py`, `test_fhir_import_smoke.py`,
  `test_fhir_query_smoke.py`, `test_health_api.py`, `test_health_ingest_user.py`,
  `test_health_tool.py`, `test_zahnfee_smoke.py`.

---

## WARUM

### Schema-SSOT (die zentrale Invariante)

- `schema.py:ENTITIES` ist die **einzige** Quelle für Feld-/Label-/Spaltennamen. Migration 023 ist die
  DDL-Quelle; die Registry mappt API↔Spalte + trägt UI-Metadaten. Das Frontend rendert generisch über
  `_schema` — es gibt **kein** handgespiegeltes `akteFields.ts`/`ENTITY_COLUMNS` mehr. Früher lagen
  Definitionen verteilt in `akteFields.ts`, `api.ts` (LABEL_FIELDS) und `AkteEntityList.tsx`
  (ENTITY_COLUMNS) und drifteten (z. B. Spalte „sicherheit" statt „schweregrad" → still leere Zelle).
  Das war die dokumentierte Ursache, dass „Agenten Schleifen drehten" (MEMORY: Akte Schema SSOT).
- **Guard-Tests in `test_akte_schema.py` erzwingen das technisch:** `spec.fields` ⊆ PRAGMA-Spalten;
  `label_fields`/`list_columns`/`numeric_fields` ⊆ `fields`; jede Entität hat ≥1 required-Feld;
  Key-Set == Lastenheft. **Wer eine Registry-Spalte ändert ohne die Migration, bricht den Test.**
- Neue Entität = ein Registry-Eintrag + eine Tabelle in der Migration. Vorher 5-Datei-Eingriff.

### Was bricht, wenn man X anfasst

- **`schema.py` ändern ohne Migration anzupassen** → Guard-Test rot (Spalte fehlt in Tabelle). Immer
  beide zusammen.
- **`date_field` einer Entität entfernen** → Einträge verschwinden aus der Timeline (timeline filtert
  `sort_date IS NOT NULL`, und `_sort_date_for` liefert None ohne date_field). `practitioners` hat
  bewusst kein date_field → Ärzte stehen nie in der Timeline (Absicht).
- **`label_fields[0]` ändern** → Tabellenkopf-Label + abgeleitetes Record-Label ändern sich
  (Frontend nimmt `label_fields[0]` als Spaltentitel und das erste gefüllte label_field als Wert).
- **`array_fields` vs. `fields`**: array_fields landen in `extra_json` (JSON-Blob), getypte Felder in
  echten Spalten. Ändert man ein array_field zu einem getypten Feld, muss eine Spalte hinzukommen,
  sonst INSERT-Fehler. `_row_to_dict` merged `extra_json` wieder flach — die UI sieht beides gleich.
- **`COMMON_FIELDS` erweitern** → muss in **jeder** der 9 Tabellen als Spalte existieren (alle haben
  external_id/quelle/confidence/verifiziert). Sonst INSERT-Fehler bei der Entität ohne die Spalte.

### Sicherheits-Invarianten

- **SQL-Injection-Fläche:** Tabellen-/Spaltennamen kommen **ausschließlich** aus der statischen
  `ENTITIES`-Registry, nie aus User-Input (deshalb sind die f-String-Interpolationen in `entities.py`
  sicher). Werte gehen immer über Parameter-Bindings. Wer `_spec`/`_split` so ändert, dass User-Keys
  ungefiltert in SQL-Namen landen, öffnet eine Injection.
- **Owner-Isolation:** Jeder Akten-Zugriff geht über `get_own_id(user)` (löst genau eine Akte je User
  auf) bzw. `_ensure_owner`. `akte_patient.owner_user_id` + WHERE-Klauseln erzwingen, dass ein User
  nur seine eigene Akte sieht. Entitäten zusätzlich per `patient_id` gebunden.
- **Health-Ingest user_id NICHT aus dem Request:** Der Health-Key bindet an genau einen konfigurierten
  User (`settings.health_ingest_user`). Würde die user_id aus dem Payload kommen, könnte ein
  geleakter Key fremde Akten überschreiben (Cross-User-PHI). Single-Device-Ingest by design.
- **Konstant-zeitiger Key-Vergleich** (`verify_secret` → `hmac.compare_digest`, Issue #180) gegen
  Timing-Side-Channels; **fail-closed** (leeres Secret ⇒ jeder Vergleich false ⇒ 403).
- **Ingest rate-limited je Client-IP** (`check_rate`) — der Endpoint ist nicht auth-geschützt
  (Gerät hat keinen JWT), daher Key+Rate-Limit als Schutz.

### Transaktions-Garantien

- **Akten-Schreibpfade** (`create`/`batch_create`) laufen in `db(immediate=True)` (BEGIN IMMEDIATE):
  serialisiert gleichzeitige Schreiber (kein TOCTOU beim external_id-Upsert: SELECT-dann-INSERT/UPDATE
  ist atomar) und macht Batch-Importe alles-oder-nichts.
- **Health-Ingest** schreibt Rohsatz + Tages-Rollup in **einer** Transaktion: scheitert der Rollup,
  rollt auch der Rohsatz zurück → keine „halbe Ingest-Spur". `backfill_daily` macht den Rollup pro
  Record in einer eigenen Transaktion (idempotent re-runnable).

### Idempotenz / Upsert

- **Akte:** `external_id` (UNIQUE-Index `(patient_id, external_id)`) macht Re-Importe idempotent
  (`_upsert` findet den Vorgänger und updatet). Der YAML-Prototyp-Importer setzt deterministische
  external_ids (`proto:{slug}:{entity}:{suffix}`).
- **FHIR:** Upsert per `(user_id, resource_type, resource_id)` (UNIQUE-Index).
- **eGA:** Upsert per `(id, user_id)`; `id` ist stabil (TK-id mit dto-Präfix oder SHA256 über
  businessObjectId/JSON-Prefix). ICD-Conditions werden je `code|display` dedupliziert.
- **Health-Daily:** `ON CONFLICT (date, metric_name, user_id)` — kumulative/zeitbasierte Metriken
  **addieren** (mehrere Ingests pro Tag summieren), sonstige bilden Mittelwert `(alt+neu)/2`.

### Routing-Reihenfolge (FastAPI matcht in Definitionsreihenfolge)

- In `patientenakte.py` müssen literale Sichten (`/_schema`, `/timeline`, `/summary`) **vor** der
  generischen `/{entity}`-Route stehen, sonst fängt `{entity}` sie als „unbekannte Entität" ab.
  Der frühere `/patients/*`-Multi-Patient-Zweig musste aus demselben Grund vor `/{entity}` liegen.

### Read-only vs. schreibbar (architektonische Trennung)

- Die **Patientenakte** (`akte_*`) ist die von Nutzer+Agenten **schreibbare** relationale Domäne.
- **eGA/FHIR** (`ega_records`/`fhir_resources`) sind **read-only Blob-Stores** für Kassendaten-Importe.
  Bewusst getrennt (SPEC.md:902–940). Die KI-Tools lesen FHIR (`query_fhir_data`), schreiben aber nie.
  Es gibt absichtlich **kein** Akten-Schreibtool für Agenten — Schreiben nur über REST.
- Das Frontend führt beide unter einer Sidebar, aber die Akten-Views (`Akte*`) sprechen
  `akteApi`/`patientenakte`, die toten Legacy-Views (`Uebersicht/Diagnosen/…`) sprachen `egaApi`/`fhirApi`.

### Datum-Heuristik

- Akte-Datumsfelder sind unsauber („2024-11-15 bis 2024-11-26", „2020", „V.a. F43.x"). `to_sort_date`
  zieht per Regex das erste YYYY[-MM[-DD]] heraus und füllt fehlende Teile mit `01`. Reine
  Sortier-Hilfe — das Originalfeld (z. B. `diagnostiziert_am`) bleibt unangetastet.

### Zahnfee-Robustheit

- `_extract_json` ist absichtlich 5-stufig (direkt → ```-Block → erstes {…} mit „open" →
  Markdown-Sektionen → ganzer Text in „open"), weil LLMs trotz JSON-Anweisung Markdown drumherum
  liefern. Der Scheduler triggert nur einmal pro Tag (Doppel-Guard: `last_run_date` + heutiges
  Briefing existiert schon). Der Recall-L2-Consolidate hängt am selben Tages-Tick (reuse des
  „Schlaf-Batch"-Fensters), läuft aber nur mit konfiguriertem Modell.

---

## Datenmodell

### Tabelle `akte_patient` (Migration 023)

`id` PK, `owner_user_id` NOT NULL, `slug`, `name`, `vorname`, `geburtsdatum`, `geburtsort`,
`geschlecht`, `blutgruppe`, `rh_faktor`, `adresse_json`, `telefon_json`, `email`,
`notfallkontakt_json`, `versicherung_json`, `beruf`, `arbeitgeber`, `external_id`,
`created_at`, `updated_at`.
Indizes: `idx_akte_patient_owner(owner_user_id)`; UNIQUE `(owner_user_id, external_id)` WHERE
external_id NOT NULL.
JSON-Felder in `patients.py:_JSON_FIELDS` = {adresse→adresse_json, telefon→telefon_json,
notfallkontakt→notfallkontakt_json, versicherung→versicherung_json}. Skalare in `_SCALAR`.

### Die 9 Entitätstabellen (`akte_condition`, `akte_medication`, `akte_observation`,
`akte_encounter`, `akte_imaging`, `akte_allergy`, `akte_practitioner`, `akte_document`, `akte_note`)

Gemeinsamer Kopf je Tabelle:
`id` PK, `patient_id` NOT NULL REFERENCES akte_patient(id) **ON DELETE CASCADE**,
`external_id`, `quelle`, `confidence REAL`, `verifiziert INTEGER NOT NULL DEFAULT 0`,
`sort_date`, `extra_json`, `created_at` NOT NULL, `updated_at` NOT NULL,
+ entity-spezifische getypte Spalten (siehe „WAS B").
Pro Tabelle: Index `(patient_id, sort_date)`; UNIQUE `(patient_id, external_id)` WHERE external_id
NOT NULL. `akte_observation` zusätzlich Index `(patient_id, parameter)`.
`akte_observation.wert`/`referenz_min`/`referenz_max` sind `REAL`; `wert_text` für nicht-numerische
Werte. (FK CASCADE setzt `foreign_keys=ON` voraus.)

### Tabelle `fhir_resources` (Migration 021)

`id` PK (uuid7), `user_id` NOT NULL, `resource_type` NOT NULL, `resource_id` NOT NULL,
`resource_json` NOT NULL, `imported_at` NOT NULL DEFAULT datetime('now').
UNIQUE `(user_id, resource_type, resource_id)`; Indizes `(user_id, resource_type)`, `(user_id)`.
`RESOURCE_LABELS` (fhir.py:13): Condition→Diagnosen, MedicationRequest/Statement→Medikamente,
Observation→Laborwerte, AllergyIntolerance→Allergien, Immunization→Impfungen, Procedure→Eingriffe,
Encounter→Arztbesuche, DiagnosticReport→Befunde, DocumentReference→Dokumente, Patient→Stammdaten.

### Tabelle `ega_records` (Migration 022)

`id` PK (stabil), `user_id` NOT NULL, `dto_type` NOT NULL, `display` NOT NULL DEFAULT '',
`sort_date`, `record_json` NOT NULL, `imported_at` NOT NULL DEFAULT datetime('now').
Indizes `(user_id, dto_type)`, `(user_id, sort_date)`.
DTO-Typen: Encounter, HospitalStay, MedicationDispense, AmbulantClaim, MedicationClaim, Procedure,
Condition. Kosten aus AmbulantClaim + MedicationClaim (Zuzahlung über `service.coding.code=="zuzahlung"`).

### Tabelle `health_ingest` (Migration 015 + 020)

`id` PK (uuid7), `received_at` NOT NULL, `automation_name`, `automation_id`, `session_id`,
`period`, `aggregation`, `payload` NOT NULL (JSON-Roh), `user_id` NOT NULL DEFAULT 'till' (ab 020).
Indizes `received_at DESC`, `automation_id`, `user_id`.

### Tabelle `health_daily` (Migration 016 + 020)

`date` NOT NULL, `metric_name` NOT NULL, `user_id` NOT NULL DEFAULT 'till', `unit` NOT NULL DEFAULT '',
`value REAL` NOT NULL. **PK (date, metric_name, user_id)** (ab 020 neu gebaut).
Indizes `date`, `user_id`.
Aggregationsklassen (health.py): `_CUMULATIVE` = {step_count, active_energy_burned,
basal_energy_burned, dietary_energy, distance_walking_running, flights_climbed, push_count,
swimming_stroke_count}; `_TIME_BASED` = {sleep_analysis, mindful_session, stand_time}.
Diese Liste ist im `ON CONFLICT`-CASE **dupliziert** (SQL-String in `_process_payload_to_daily`) —
Drift-Risiko (siehe Offene Enden).

### Config-Dateien (kein DB-Table)

- `HH_CONFIG_DIR/zahnfee.json` — `ZahnfeeConfig` (enabled, model, run_hour, lookback_hours,
  source_datamining, source_mail, soul). PUT-Schema `ConfigBody` validiert (run_hour 0–23,
  lookback_hours 1–720, model ≤200 Zeichen, soul ≤8000).
- `HH_DATA_DIR/zahnfee_briefing.json` — `Briefing` (generated_at, date, open_items, went_well,
  went_badly, today, error?).

### Env-Vars / Settings-Keys

- `HH_HEALTH_API_KEY` → `settings.health_api_key` (Pflicht für Ingest; leer ⇒ 403).
- `HH_HEALTH_INGEST_USER` → `settings.health_ingest_user` (Default „till").
- `settings.config_dir`, `settings.data_dir` (Zahnfee-Pfade).
- `settings.agentlink_url` (steuert nur indirekt: ask_agent-Tool, nicht Akte).

### Apple-Health-Metriknamen (Frontend `METRIC_LABELS`, _TrendChart.tsx)

40+ Mappings, u. a. step_count, distance_walking_running, active_energy_burned/active_energy,
basal_energy_burned, apple_exercise_time, flights_climbed, apple_stand_hour/_time, physical_effort,
six_minute_walking_test_distance, heart_rate, resting_heart_rate, walking_heart_rate_average,
heart_rate_variability, blood_oxygen_saturation, respiratory_rate, breathing_disturbances,
walking_speed, walking_step_length, walking_asymmetry_percentage, walking_double_support_percentage,
stair_speed_up/down, headphone_audio_exposure, environmental_audio_exposure, time_in_daylight,
apple_sleeping_wrist_temperature. Schlaf (`sleep_analysis`) separat in `_SleepChart`.

---

## Offene Enden

### Tote / verwaiste Frontend-Views (Aufräum-Kandidaten)

Folgende Views liegen in `features/health/views/` und werden von **keiner** anderen Datei referenziert
(weder Route noch Import) — Leichen einer früheren eGA/FHIR-basierten UI:
`UebersichtView.tsx`, `DiagnosenView.tsx`, `LaborwerteView.tsx`, `MedikamenteView.tsx`,
`ArztabrechnungView.tsx`, `ResearchApisView.tsx`, `SimpleListView.tsx`, `KiAssistentView.tsx`,
`ZeitstrahlView.tsx`. Die `EgaImportButton.tsx`/`FhirImportButton.tsx`-Komponenten werden **nur** vom
toten `UebersichtView` benutzt → effektiv ungenutzt. (`ResearchApisView` hat sogar ein lebendes
Backend `api/routes/research_apis.py` + `researchApi` in api.ts, ist aber im Frontend nicht verlinkt.)

### Import-Funktion im Frontend ist ein Platzhalter

`HealthPage.tsx:ImportView` rendert nur „Import-Funktionen werden in Kürze verfügbar sein." Die
funktionierenden Upload-Buttons (`EgaImportButton`/`FhirImportButton`) sind nicht verdrahtet. Die
**Backend-Import-Endpoints (`/api/modules/patientenakte/ega/import`, `/api/modules/patientenakte/fhir/import`, `/api/modules/patientenakte/fhir/import-ega`) sind aber
voll funktionsfähig** — nur die UI fehlt. Wer eGA/FHIR importieren will, muss aktuell direkt die API
ansprechen.

### `ki`-Route zeigt die falsche View

`HealthPage.tsx:74` mappt `ki` auf `AppleHealthView` (Apple-Health-Trends) statt auf einen KI-Assistenten.
Der `KiFloatingButton` navigiert nach `/health/ki` (mit `state.resourceType`), aber dort erscheinen
Health-Charts, kein Chat. Die echte KI-View (`KiAssistentView.tsx`, nutzt `buddyApi`/`chat`) ist tot.
Inkonsistenz zwischen Button-Intention und Route-Ziel.

### Workouts werden gezählt aber nicht verarbeitet

`health_data.py:ingest` zählt `workouts` in der Antwort, aber `_process_payload_to_daily` verarbeitet
nur `data.metrics` — `data.workouts` wird nie in `health_daily` o. ä. geschrieben. Workout-Daten gehen
nur als Roh-Payload in `health_ingest`, sind aber nirgends abfragbar/aggregiert.

### Doppelte Metrik-Klassenliste (Drift-Risiko)

Die kumulativen/zeitbasierten Metriknamen stehen zweimal: einmal als Python-Sets `_CUMULATIVE`/
`_TIME_BASED` (health.py:78/84, für `_aggregate_samples`) und ein zweites Mal hartcodiert im
`ON CONFLICT … DO UPDATE`-SQL-String (health.py:138–143). Ändert man eine Liste ohne die andere,
aggregiert der erste Ingest eines Tages anders als jeder weitere (Summe vs. Mittelwert). Sollte aus
einer Quelle generiert werden.

### `?key=`-Query-Pfad für Health-Ingest (deprecated, noch aktiv)

`health_data.py:_check_key` akzeptiert den Key noch als `?key=`-Query-Parameter (landet in
Access-/Proxy-Logs). Markiert als #207, Warn-Log gesetzt, aber noch nicht entfernt — soll raus, sobald
der Client auf den Header umgestellt ist.

### Hardcodierte Laborreferenzbereiche im Frontend

`AkteLabCharts.tsx:REFERENCE_RANGES` enthält 10 hardcodierte Referenzbereiche (HbA1c, eGFR, GPT, GOT,
Cholesterin-Varianten, Triglyceride, Nüchternglukose). Kommentar „Iteration 2: aus Entität extrahieren"
— die Entität hat eigene `referenz_min`/`referenz_max`-Felder, die hier ignoriert werden. Drift, wenn
ein importierter Wert andere Referenzen hat als die Frontend-Konstante.

### `import_proto.py` nicht in die API verdrahtet

Der YAML/CSV-Prototyp-Importer hat **keinen** API-Endpoint — er ist nur als CLI (`__main__`) und im
Test (`test_akte_import.py`) aufrufbar. Ein Restbestand der Erst-Befüllung aus `akten/<slug>/`.
Verworfene Felder werden geloggt (`import_akte`-Warn bei nicht-mappbaren Ereignis-Feldern), aber still
verworfen, nicht in `extra_json` gerettet.

### `backfill_daily` Default-User-Hardcode

`health.py:backfill_daily(user_id="till")` hat „till" als Default fest verdrahtet (Single-User-Annahme).
Nicht über einen Endpoint erreichbar (nur in Tests aufgerufen) — manuelle Wartungsfunktion.

### Single-User-Annahme („jeder User eine Akte")

Die ehemalige Multi-Patient-/spekulative Mehrmandantenfähigkeit (`/patients/*`-Route) wurde 2026-06
entfernt (#195, Kommentar in patientenakte.py:100–103). `get_own_id` nimmt `LIMIT 1` auf
owner_user_id — die DB könnte theoretisch mehrere Akten je User halten (UNIQUE nur auf external_id,
nicht auf owner_user_id), aber die API spricht immer nur die erste an. Wer je mehr als eine Akte je
User anlegt (z. B. direkter DB-Write), bekommt nicht-deterministisches Verhalten.

### Zahnfee außerhalb von `features/health/`

Obwohl die Zahnfee-Config-UI laut SPEC.md:757/875 im Health-Bereich sitzen soll, liegt im
`features/health/`-Ordner **kein** Zahnfee-Frontend. Der `/api/zahnfee/*`-Router existiert, aber die
verbrauchende UI (Briefing-Anzeige, Config) wird woanders gerendert (Buddy-/Dashboard-Kontext) — die
Verortung „Zahnfee = Health" gilt nur konzeptionell, nicht im Code-Layout.

### FHIR-`timeline` sortiert nach Import-Zeit, nicht nach klinischem Datum

`fhir_db.timeline` ORDER BY `imported_at DESC` (nicht nach dem medizinischen Ereignisdatum der
Ressource). Die eGA-/Akte-Timelines nutzen dagegen `sort_date` (Ereignisdatum). Wer FHIR-Daten
chronologisch nach Behandlung erwartet, bekommt stattdessen Import-Reihenfolge.
