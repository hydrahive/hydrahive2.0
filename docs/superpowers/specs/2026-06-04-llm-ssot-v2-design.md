# LLM-SSOT v2 — Design (Sub-Projekt 2: alle übrigen Picker auf die eine Quelle)

> **Ziel:** Die Vereinheitlichung aus SP1 vollenden — **jeder** verbleibende Modell-Picker liest
> aus der einen kanonischen Quelle (`GET /api/llm/models`), die alten divergenten Pfade werden
> gelöscht. Danach: eine Quelle, überall dieselbe sortierte Liste, keine Abweichungen mehr.
>
> **Scope = Sub-Projekt 2:** die 6 verbliebenen Frontend-Aufrufer von `llmInfoApi.getModels()`
> (dem alten `/llm`+`/llm/catalog`-Merge) auf `llmModelsApi.byModality("chat")` umstellen +
> toten/divergenten Alt-Code entfernen. Backend (validate, Buddy-`/models`) ist seit SP1 schon
> auf der Registry — wird nicht angefasst.
>
> **Status:** Design abgestimmt (Brainstorming 2026-06-04, Till). Voraussetzung: SP1 auf main
> (`dab514fc`). Map: code-explorer 2026-06-04.

---

## Entscheidungen (abgestimmt)

| Frage | Entscheidung |
|---|---|
| Picker-Quelle | Alle Chat-Modell-Picker → `llmModelsApi.byModality("chat")` (nur id-Liste nötig; `_ModelTab`-Free-Badge nutzt `is_free`, hat `RegistryModel`). |
| `default_model`-Vorauswahl | `GET /api/llm/models?modality=` liefert zusätzlich `default` (= `get_default(modality)`, nicht-geheim). NewProject/NewAgent behalten die Default-Vorauswahl. |
| Alt-Code | Toter/divergenter Code löschen: `MediaModelsSection`, `llmInfoApi.getModels`, die 4 Modalitäts-Frontend-Helfer + Typen, die 4 Modalitäts-Backend-**Routen**. |
| `/llm/catalog` + CatalogPage | **Bleibt** — der Admin-Katalog-Browser braucht volle Metadaten (family/modalities/Preise), die `RegistryModel` nicht trägt. |

---

## Ausgangslage (was SP1 schon unified hat — NICHT anfassen)
- `DefaultModelsSection.tsx` nutzt `llmModelsApi.byModality(p)` (7 Zwecke).
- `GET /api/llm/models` (`routes/llm.py`, require_auth) + `llmModelsApi.byModality()` (`features/llm/api.ts`).
- `agents/_validation.py::_available_models()` liest `registry.known_ids()`.
- Buddy: `/api/buddy/models` → `commands.list_models` → `_available_models()` → schon Registry. (Der Frontend-`ModelPicker` ruft NICHT `/buddy/models`, sondern `llmInfoApi.getModels()` → genau das ist SP2.)
- `media_models.*` / `embed.available_for_config` (von Registry + Tools genutzt) — bleiben.

---

## A. Endpoint-Erweiterung: `default` in der Antwort

`GET /api/llm/models[?modality=]` (`routes/llm.py`) gibt zusätzlich ein `default`-Feld zurück:
```json
{ "models": [ … ], "default": "<get_default(modality) or ''>" }
```
- `default` = `_config.get_default(modality)` wenn `modality` gesetzt und ein gültiger Zweck ist; sonst `get_default("chat")` (kein modality → Chat-Default) bzw. `""`.
- Nicht-geheim (nur ein Modell-Name). `require_auth` bleibt.
- `RegistryModel`-Frontend-Typ unverändert; ein neuer Response-Typ `{ models: RegistryModel[]; default: string }` für `byModality`.

## B. Frontend-Migration (6 Aufrufer)

Alle ersetzen `llmInfoApi.getModels()` durch `llmModelsApi.byModality("chat")` (liefert jetzt `{models, default}`):

| Aufrufer | Datei | heute → neu |
|---|---|---|
| `ModelPicker` (Chat) | `features/chat/ModelPicker.tsx` | `.models`(string[]) → `models.map(m=>m.id)` (sortiert kommt schon vom Backend). Deckt transitiv `SessionModelControls` + `ZahnfeePage` (nutzen den ModelPicker). |
| Chat-`/model`-Command | `features/chat/commands.ts` | `.models` (id-Liste für Anzeige + Validierung) → `byModality("chat")` ids. |
| `AgentsPage` | `features/agents/AgentsPage.tsx` | holt `models`/`catalog`/`default_model` → künftig `byModality("chat")`: `models=res.models.map(id)`, der `catalog`-Prop für `_ModelTab` wird `res.models` (`RegistryModel[]`), `defaultModel=res.default`. |
| `_ModelTab` | `features/agents/_ModelTab.tsx` | Prop-Typ `CatalogModel[]`→`RegistryModel[]`; rendert `id` + `is_free`-Badge (beide vorhanden). |
| `CompactionSection` | `features/agents/CompactionSection.tsx` | `models:string[]`-Prop bleibt (von AgentsPage gefüllt). |
| `NewAgentDialog` | `features/agents/NewAgentDialog.tsx` | `models`+`defaultModel`-Props bleiben (gefüllt aus `byModality`). |
| `BuddySettingsPage` → `BuddySettingsCompaction` | `features/buddy/BuddySettingsPage.tsx` | `.models` → `byModality("chat")` ids. |
| `NewProjectDialog` | `features/projects/NewProjectDialog.tsx` | eigener `getModels`-Fetch → `byModality("chat")`; Vorauswahl `res.default || res.models[0]?.id`. |

> Sortierung: das Backend sortiert schon (provider, label) — die Picker brauchen kein eigenes `.sort()` mehr (alt: `[...info.models].sort()`).

## C. Löschen (Alt-Code, nach der Migration)

**Frontend:**
- `features/llm/MediaModelsSection.tsx` (ganze Datei — tot seit SP1).
- `features/agents/api.ts`: `llmInfoApi.getModels` + `llmInfoApi`-Export + `LlmProviderInfo`-Typ (nach Migration der 6 Aufrufer).
- `features/llm/api.ts`: `getEmbedModels/getSpeechModels/getTranscribeModels/getVideoModels` + Typen `EmbedModel/SpeechModel/VideoModel/TranscribeModel` (einzige Nutzer waren das tote MediaModelsSection).

**Backend (`routes/llm.py`) — nur die HTTP-Routen, die Funktionen bleiben:**
- `GET /api/llm/embed-models`, `/speech-models`, `/transcribe-models`, `/video-models`.
- (Die zugrundeliegenden `embed.available_for_config`, `media_models.list_speech_models/list_transcribe_models/list_video_models` bleiben — Registry + Tools nutzen sie direkt.)

## D. Bleibt unverändert
- `/api/llm/catalog` + `catalogApi` + `CatalogPage.tsx` (Admin-Katalog-Browser, volle Metadaten).
- `media_models.*`, `embed.*`, `registry.*`, `_validation._available_models`, Buddy-Backend, `/api/tts/voices`.

---

## Datenfluss (nach SP2)
Jeder Picker → `GET /api/llm/models?modality=chat` → `{models: [sortiert], default}` → rendert `models` + selektiert `default`. Modell setzen → bestehender Pfad (`agentsApi.update`/`buddyApi.setModel`) → `validate_model` (Registry, seit SP1). **Eine Quelle, ein Endpoint, überall dieselbe Liste.**

## Fehlerbehandlung
- Picker-Fetch schlägt fehl → sichtbarer Fehler bzw. leere Liste (kein stilles Schlucken); bestehende Picker-Fehleranzeige beibehalten/verbessern.
- Leere Registry (kein Provider) → leere Liste + `default=""` → Picker zeigt leer, kein Crash.

## Tests
- **Backend:** `/api/llm/models` liefert `default` korrekt (= `get_default(modality)`, chat bei fehlendem modality); non-admin weiterhin erlaubt.
- **Frontend:** `npm run build` + eslint grün nach Migration + Löschungen; keine toten Imports (`MediaModelsSection`, `llmInfoApi`, `get*Models` weg ohne dangling refs).
- **Regression:** volle Backend-Suite grün (insb. keine Referenzen auf gelöschte Routen in Tests — falls Tests `/embed-models` etc. treffen, mit-anpassen).
- **Live-E2E auf `.23`:** Buddy, Werkstatt-Chat, Agent-Edit, Neues Projekt zeigen **dieselbe** Modell-Liste; Default vorausgewählt; Wechsel rastet ein.

## Bewusst NICHT in v2 (YAGNI)
- TTS-Voices in `/api/llm/models` aufnehmen (kein Picker braucht's; Voices laufen serverseitig + `/api/tts/voices`).
- `/llm/catalog` o.ä. ersetzen/zusammenlegen (CatalogPage braucht die vollen Metadaten — eigenständig sinnvoll).
- Speicher-Key-Normalisierung (SP1-Backlog, bleibt).

## In der Planungs-Phase zu klären (Detail, kein Blocker)
- Genaue `_ModelTab`-Anpassung (CatalogModel→RegistryModel): welche Felder das Template wirklich rendert (id + is_free) — Rest streichen.
- Ob ein Test eine der gelöschten Routen (`/embed-models` …) trifft → mit-entfernen/anpassen.
- `NewProjectDialog`-Default: `res.default || res.models[0]?.id`.
