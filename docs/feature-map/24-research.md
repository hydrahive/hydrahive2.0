# Research

Subsystem: **Forschungs-API-Registry** ("Research APIs"). Eine system-weite,
admin-konfigurierbare Registry externer wissenschaftlicher/medizinischer REST-APIs
(PubMed, OpenAlex, openFDA, ClinicalTrials.gov, …). Sie tut **nicht** selbst Recherche.
Sie ist eine **Auth-Injektions-Schicht zweiter Stufe** für das `fetch_url`-Tool: wenn ein
Agent eine externe Wissenschafts-API per `fetch_url` abruft und der Admin dafür einen Key
hinterlegt hat, wird der Key transparent eingehängt — der Agent sieht ihn nie. Die
eigentliche "Recherche-Intelligenz" (welche Quelle, welcher Endpoint, welche Query) lebt
in einem System-Skill (`medical-research.md`), nicht in Python-Code.

Code-Umfang: 5 Python-Dateien (`research/`, ~330 Zeilen inkl. Tests-Setup), 1 Route-Datei
(52 Zeilen), 1 Frontend-View (170 Zeilen), 1 Frontend-API-Client-Block (~35 Zeilen),
1 System-Skill (Markdown, 100 Zeilen), 1 Test-Datei (178 Zeilen).

---

## WAS

Jede Fähigkeit / jeder Endpoint / jedes Feld / jede UI-Komponente einzeln:

### Backend-Datenmodell (`research/models.py`)
- **`ResearchApi` dataclass** — beschreibt eine externe Quelle.
- **`CATEGORIES`** Tupel — die 4 erlaubten Kategorien: `"literatur"`, `"medikamente"`, `"krankheiten_gene"`, `"studien"`.
- **`AUTH_TYPES`** Tupel — die 4 erlaubten Auth-Typen: `"none"`, `"query"`, `"header"`, `"bearer"`.
- **`ResearchApi.id`** — eindeutige String-ID (z.B. `"pubmed"`, `"core"`).
- **`ResearchApi.name`** — Anzeigename (z.B. `"PubMed / NCBI E-utilities"`).
- **`ResearchApi.category`** — eine der 4 CATEGORIES.
- **`ResearchApi.base_url`** — Basis-URL; wird für den Reachability-Test (`POST .../test`) angefragt.
- **`ResearchApi.url_pattern`** — Glob-Pattern (z.B. `https://api.fda.gov/*`) für das Matching gegen die `fetch_url`-Ziel-URL.
- **`ResearchApi.docs_url`** — Doku-Link, im Frontend als "Docs ↗" verlinkt.
- **`ResearchApi.description`** — Kurzbeschreibung (Frontend-Text).
- **`ResearchApi.needs_key`** (bool) — `True` = ohne Key nicht nutzbar; nur UI-Hinweis ("Key nötig"-Badge). **Wird in keiner Backend-Logik konsumiert.**
- **`ResearchApi.auth_type`** — `none|query|header|bearer`; steuert, wie der Key injiziert wird.
- **`ResearchApi.auth_param`** — Query-Param-Name (bei `query`) bzw. Header-Name (bei `header`); bei `bearer`/`none` leer.
- **`ResearchApi.polite_email_param`** — z.B. `"mailto"` (OpenAlex/Crossref Polite-Pool); **rein dokumentarisch, in keiner Logik konsumiert** (kein Secret).
- **`ResearchApi.rate_limit`** — Freitext-Hinweis zum Rate-Limit (Frontend-Text).
- **`ResearchApi.enabled`** (bool) — ob die Quelle aktiv ist.
- **`ResearchApi.key`** (Secret) — der API-Key/Token; in der Registry AES-GCM-verschlüsselt persistiert.
- **`ResearchApi.public_dict()`** — Methode: liefert das Dict **ohne** Klartext-`key`, stattdessen mit `has_key`-Bool-Flag (für GET/Frontend).

### Seed-Daten (`research/_seed.py` — 15 vorbefüllte Quellen)
**Literatur (`literatur`):**
- **`pubmed`** — PubMed/NCBI E-utilities. `auth_type=query`, `auth_param=api_key`, `needs_key=False` (optionaler Key = höheres Limit), enabled.
- **`europepmc`** — Europe PMC. `auth_type=none`, enabled.
- **`openalex`** — OpenAlex. `auth_type=none`, `polite_email_param=mailto`, enabled.
- **`semanticscholar`** — Semantic Scholar (S2). `auth_type=header`, `auth_param=x-api-key`, `needs_key=False` (optional), enabled.
- **`crossref`** — Crossref. `auth_type=none`, `polite_email_param=mailto`, enabled.
- **`core`** — CORE. `auth_type=bearer`, `needs_key=True`, **`enabled=False`** (startet aus, Key nötig).
- **`biorxiv`** — bioRxiv/medRxiv. `auth_type=none`, enabled.

**Medikamente (`medikamente`):**
- **`openfda`** — openFDA. `auth_type=query`, `auth_param=api_key`, `needs_key=False` (optional), enabled.
- **`rxnorm`** — RxNorm/RxNav (NLM). `auth_type=none`, enabled.

**Krankheiten/Gene (`krankheiten_gene`):**
- **`icd11`** — ICD-11 API (WHO). `auth_type=bearer`, `needs_key=True`, **`enabled=False`** (OAuth, Token manuell als Bearer eintragen).
- **`mygene`** — MyGene.info. `auth_type=none`, enabled.
- **`myvariant`** — MyVariant.info. `auth_type=none`, enabled.
- **`opentargets`** — Open Targets (GraphQL). `auth_type=none`, enabled.
- **`hpo`** — Human Phenotype Ontology. `auth_type=none`, enabled.

**Studien (`studien`):**
- **`clinicaltrials`** — ClinicalTrials.gov API v2. `auth_type=none`, enabled.

> Hinweis: Der Test fordert `len(SEED) >= 12`, der Seed-Header-Kommentar spricht von "15 Quellen", die tatsächliche Liste enthält **15** Einträge (Commit-Titel sagt ebenfalls "15 Quellen"). Kein Drift hier, nur ein lascher Test-Mindestwert.

### Store-Funktionen (`research/store.py`)
- **`_load_overrides()`** — lädt `research_apis.json`, entschlüsselt persistierte Keys; toleriert defektes JSON (Warnung, `{}`) und nicht-entschlüsselbare Keys (Warnung, Key gedroppt).
- **`_save_overrides(overrides)`** — verschlüsselt Keys, schreibt atomar (`.tmp` → `replace`), `chmod 0600`.
- **`list_apis()`** — merged SEED + Overrides (`key`/`enabled`), liefert `list[ResearchApi]`.
- **`get_api(rid)`** — einzelne API per ID (oder `None`).
- **`list_public()`** — `list[dict]` ohne Klartext-Keys (für Frontend).
- **`_set_override(rid, **fields)`** — validiert ID gegen SEED, schreibt Override; `False` wenn ID unbekannt.
- **`set_key(rid, key)`** — setzt Key-Override.
- **`set_enabled(rid, enabled)`** — setzt enabled-Override.
- **`match_research_api(url)`** — Kern-Injektions-Funktion: liefert das erste aktivierte, key-tragende Registry-Match als `Credential`-Äquivalent (oder `None`).

### Package-Exports (`research/__init__.py`)
Re-exportiert: `ResearchApi`, `get_api`, `list_apis`, `list_public`, `match_research_api`, `set_enabled`, `set_key`.

### API-Endpoints (`api/routes/research_apis.py`, Prefix `/api/research-apis`, Tag `research-apis`, **alle admin-only**)
- **`GET /api/research-apis`** — `list_apis()`-Handler → `{"apis": [...public_dict...]}`. Keys maskiert.
- **`PATCH /api/research-apis/{rid}`** — `update_api()`-Handler. Body `ApiUpdate{enabled?, key?}`. 404 wenn ID unbekannt. Setzt enabled und/oder key, liefert aktualisiertes `public_dict()`.
- **`POST /api/research-apis/{rid}/test`** — `test_api()`-Handler. Reachability-Check: `httpx.GET` auf `base_url` (10s Timeout, follow_redirects). Liefert `{"ok": status<500, "status": code}` bzw. `{"ok": False, "error": str}`.
- **`ApiUpdate` Pydantic-Model** — `enabled: bool | None`, `key: str | None`.

### `fetch_url`-Integration (`tools/fetch_url.py`)
- **`_select_cred(user_id, url, auth_name)`** — wählt Auth-Credential: per-User-Credential hat Vorrang; nur wenn keins matcht **und** kein `auth_name` erzwungen → Registry-Fallback via `match_research_api(url)`.
- **`_apply_auth(cred, headers, params)`** — hängt Auth physisch ein (bearer/basic/cookie/header/query); liefert Klartext-Hinweis nur fürs Logging, **nie** ins tool_result.
- Das `fetch_url`-Tool selbst (`TOOL`, `category="web"`) ist der einzige Konsument der Registry.

### Frontend (`frontend/src/features/health/`)
- **`researchApi` Client-Objekt** (`api.ts:170`) — 3 Methoden:
  - **`researchApi.list()`** — `GET /research-apis`.
  - **`researchApi.update(id, {enabled?, key?})`** — `PATCH /research-apis/{id}`.
  - **`researchApi.test(id)`** — `POST /research-apis/{id}/test`.
- **Typen** (`api.ts`): `ResearchCategory`, `ResearchApiPublic`, `ResearchTestResult`.
- **`ResearchApisView`** Komponente (`views/ResearchApisView.tsx:125`) — Hauptansicht; gruppiert APIs nach Kategorie, lädt per `researchApi.list()`, zeigt Admin-Fehler-Fallback.
- **`ApiCard`** Sub-Komponente (`ResearchApisView.tsx:18`) — eine Karte pro API mit: enabled-Toggle (Checkbox), Key-Eingabefeld (Passwort, nur wenn `auth_type !== "none"`), Speichern-Button, Docs-Link, Test-Button + Test-Ergebnis-Anzeige.
- **`CATEGORY_LABELS`** / **`CATEGORY_ORDER`** (`ResearchApisView.tsx:10/16`) — Emoji-Labels und Reihenfolge der 4 Kategorien.
- UI-Badges: "Key nötig" (amber, wenn `needs_key && !has_key`), "Key gesetzt" (emerald, wenn `has_key`), "aktiv"/"aus".

### System-Skill (`skills/system_defaults/medical-research.md`)
- **Skill `medical-research`** — Frontmatter: `name`, `description`, `when_to_use`, `tools_required: [fetch_url]`. Liefert dem Agenten konkrete `fetch_url`-Aufrufe pro Quelle (PubMed-2-Schritt, Europe PMC, OpenAlex, Semantic Scholar, Crossref, CORE, openFDA, RxNorm, MyGene/MyVariant, Open Targets GraphQL, HPO, ICD-11, ClinicalTrials.gov). **Dies ist die einzige Stelle, die Agenten "Recherche beibringt".**

### Config / Settings
- **`settings.research_apis_config`** (`settings/_paths.py:98`) — `config_dir / "research_apis.json"`. Pfad der Override-Datei.

---

## WIE

### Lese-/Konfigurations-Fluss (Admin im Frontend)
1. Admin öffnet die `ResearchApisView` → `useEffect` ruft `researchApi.list()` → `GET /api/research-apis`.
2. Route-Handler `list_apis()` (`research_apis.py:24`) → `require_admin`-Dependency prüft Rolle → `research.list_public()`.
3. `list_public()` → `list_apis()` → `_load_overrides()` liest `research_apis.json`, entschlüsselt Keys → merged jeden SEED-Eintrag mit seinem Override (`{**base.__dict__, **override[key/enabled]}`) → `public_dict()` strippt den Key, setzt `has_key`.
4. Frontend rendert pro Kategorie (`CATEGORY_ORDER`) eine Gruppe von `ApiCard`s.

### Toggle/Key-Schreib-Fluss
1. Admin klickt Checkbox → `toggle()` → `researchApi.update(id, {enabled: !api.enabled})` → `PATCH /api/research-apis/{rid}`.
2. Handler `update_api()` (`research_apis.py:29`): 404-Guard via `get_api(rid)` → bei `enabled`: `research.set_enabled` → bei `key`: `research.set_key` → liefert frisches `public_dict()`.
3. `set_enabled`/`set_key` → `_set_override(rid, ...)`: validiert ID gegen SEED (sonst `False`) → lädt Overrides → `overrides.setdefault(rid, {}).update(fields)` → `_save_overrides`.
4. `_save_overrides`: jedes Override-Dict mit `key` → `encrypt(key, data_dir)` (AES-GCM, Präfix `enc:v1:`) → atomarer Write (`.json.tmp` → `replace`) → `chmod 0600`.
5. Admin tippt Key + Speichern → `saveKey()` → `researchApi.update(id, {key})` → derselbe PATCH-Pfad.

### Reachability-Test-Fluss
1. Admin klickt "Test" → `runTest()` → `researchApi.test(id)` → `POST /api/research-apis/{rid}/test`.
2. Handler `test_api()` (`research_apis.py:40`): 404-Guard → `httpx.AsyncClient(timeout=10, follow_redirects=True).get(base_url)` → `{"ok": status<500, "status": code}` bzw. Fehler.
3. **Wichtig:** Der Test geht direkt über `httpx`, **nicht** über `fetch_url`/`safe_async_client` — also **ohne SSRF-Schutz** und **ohne Key-Injektion** (Keyless-Reachability auf die `base_url`).

### Auth-Injektions-Fluss (der eigentliche Zweck — Agent ruft externe Quelle)
1. Agent ruft `fetch_url`-Tool mit z.B. `url=https://api.core.ac.uk/v3/search/works?q=...`.
2. `_execute` (`fetch_url.py:81`): URL-Validierung, SSRF-Check (`is_blocked_host`), Methode validieren.
3. `_select_cred(ctx.user_id, url, auth_name)` (`fetch_url.py:69`):
   - `match_credential(user_id, url, prefer_name=auth_name)` zuerst (per-User-Credential-Store).
   - Wenn **kein** User-Cred **und kein** erzwungenes `auth_name` → `match_research_api(url)`.
4. `match_research_api(url)` (`store.py:95`): iteriert `list_apis()`, nimmt das **erste** Eintrag mit `enabled and key and auth_type in (query|header|bearer)`, dessen `url_pattern` per `matches_url` matcht → baut ein `Credential`-Objekt (`name=f"research:{id}"`, `type=auth_type`, `value=key`, `header_name`/`query_param` je nach Typ).
5. `_apply_auth(cred, headers, params)` (`fetch_url.py:46`) hängt den Key ein: bearer → `Authorization: Bearer …`, header → `headers[auth_param]`, query → `params[auth_param]`.
6. Request über `safe_async_client` (IP-gepinnt, DNS-Rebinding-sicher). Response-Body zurück; `auth_used = cred.name` (z.B. `research:core`) im Output, aber **kein** Key-Wert, **keine** Response-Header.

### Seed-Merge-Invariante (zentrale Mechanik)
Persistiert werden **nur Overrides** (`key`, `enabled`) pro ID, nicht die ganze API. Beim Laden wird jede SEED-Quelle mit ihrem Override gemerged. → Neue Seed-Quellen erscheinen automatisch nach Deploy; Admin-Edits an Bestands-Quellen bleiben erhalten. SEED ist die einzige Quelle für alle nicht-overridebaren Felder (url_pattern, auth_type, etc.).

---

## WO

Backend Research-Modul:
- `core/src/hydrahive/research/__init__.py:1` — Package-Re-Exports.
- `core/src/hydrahive/research/models.py:15` — `@dataclass ResearchApi`.
- `core/src/hydrahive/research/models.py:11` — `CATEGORIES` Tupel.
- `core/src/hydrahive/research/models.py:12` — `AUTH_TYPES` Tupel.
- `core/src/hydrahive/research/models.py:32` — `ResearchApi.public_dict()`.
- `core/src/hydrahive/research/_seed.py:10` — `SEED: list[ResearchApi]` (15 Einträge).
- `core/src/hydrahive/research/_seed.py:12` — `pubmed`.
- `core/src/hydrahive/research/_seed.py:50` — `core` (needs_key/bearer/disabled).
- `core/src/hydrahive/research/_seed.py:65` — `openfda`.
- `core/src/hydrahive/research/_seed.py:81` — `icd11` (needs_key/bearer/disabled).
- `core/src/hydrahive/research/_seed.py:115` — `clinicaltrials`.
- `core/src/hydrahive/research/store.py:21` — `_OVERRIDE_FIELDS = ("key", "enabled")`.
- `core/src/hydrahive/research/store.py:24` — `_load_overrides()`.
- `core/src/hydrahive/research/store.py:44` — `_save_overrides()`.
- `core/src/hydrahive/research/store.py:60` — `list_apis()` (Seed-Merge).
- `core/src/hydrahive/research/store.py:70` — `get_api()`.
- `core/src/hydrahive/research/store.py:74` — `list_public()`.
- `core/src/hydrahive/research/store.py:78` — `_set_override()`.
- `core/src/hydrahive/research/store.py:87` — `set_key()`.
- `core/src/hydrahive/research/store.py:91` — `set_enabled()`.
- `core/src/hydrahive/research/store.py:95` — `match_research_api()`.

API-Route:
- `core/src/hydrahive/api/routes/research_apis.py:15` — `router = APIRouter(prefix="/api/research-apis", ...)`.
- `core/src/hydrahive/api/routes/research_apis.py:18` — `class ApiUpdate`.
- `core/src/hydrahive/api/routes/research_apis.py:23` — `GET ""` → `list_apis()`.
- `core/src/hydrahive/api/routes/research_apis.py:28` — `PATCH "/{rid}"` → `update_api()`.
- `core/src/hydrahive/api/routes/research_apis.py:39` — `POST "/{rid}/test"` → `test_api()`.
- `core/src/hydrahive/api/main.py:29` — Import `research_apis_router`.
- `core/src/hydrahive/api/main.py:131` — `app.include_router(research_apis_router)`.

Auth/Crypto/Integration:
- `core/src/hydrahive/api/middleware/auth.py:53` — `require_admin` (alle Endpoints hängen daran).
- `core/src/hydrahive/credentials/_crypto.py:56` — `encrypt()`.
- `core/src/hydrahive/credentials/_crypto.py:63` — `decrypt()`.
- `core/src/hydrahive/credentials/_crypto.py:22` — Präfix `enc:v1:`.
- `core/src/hydrahive/credentials/models.py:13` — `Credential` dataclass (von `match_research_api` zurückgegeben).
- `core/src/hydrahive/credentials/models.py:28` — `matches_url()` (Glob-Match für `url_pattern`).
- `core/src/hydrahive/credentials/store.py:113` — `match_credential()` (per-User, hat Vorrang).
- `core/src/hydrahive/tools/fetch_url.py:69` — `_select_cred()` (Precedence-Logik).
- `core/src/hydrahive/tools/fetch_url.py:76-77` — lazy Import + Aufruf `match_research_api`.
- `core/src/hydrahive/tools/fetch_url.py:46` — `_apply_auth()`.
- `core/src/hydrahive/settings/_paths.py:98` — `research_apis_config` Property.

Frontend:
- `frontend/src/features/health/api.ts:145` — `ResearchCategory` Typ.
- `frontend/src/features/health/api.ts:147` — `ResearchApiPublic` Interface.
- `frontend/src/features/health/api.ts:164` — `ResearchTestResult` Interface.
- `frontend/src/features/health/api.ts:170` — `researchApi` Client (list/update/test).
- `frontend/src/features/health/views/ResearchApisView.tsx:18` — `ApiCard`.
- `frontend/src/features/health/views/ResearchApisView.tsx:125` — `ResearchApisView`.
- `frontend/src/features/health/views/ResearchApisView.tsx:10` — `CATEGORY_LABELS`.
- `frontend/src/features/health/views/ResearchApisView.tsx:16` — `CATEGORY_ORDER`.

Skill & Tests:
- `core/src/hydrahive/skills/system_defaults/medical-research.md:1` — System-Skill `medical-research`.
- `core/tests/test_research_apis.py:8` — `test_seed_integrity`.
- `core/tests/test_research_apis.py:32` — `test_store_roundtrip_and_seed_merge`.
- `core/tests/test_research_apis.py:51` — `test_public_list_masks_key`.
- `core/tests/test_research_apis.py:63` — `test_match_injects_bearer_and_query`.
- `core/tests/test_research_apis.py:78` — `test_match_none_for_keyless_or_disabled`.
- `core/tests/test_research_apis.py:89` — `test_route_list_masks_and_update`.
- `core/tests/test_research_apis.py:110` — `test_route_registered`.
- `core/tests/test_research_apis.py:119` — `test_medical_research_skill_parses`.
- `core/tests/test_research_apis.py:133` — `test_select_cred_precedence`.
- `core/tests/test_research_apis.py:164` — `test_load_overrides_tolerates_undecryptable_key`.

---

## WARUM

Die nicht-offensichtliche Verdrahtung, Annahmen, Invarianten, Gotchas:

- **Die Registry "tut" keine Recherche.** Sie ist nur ein Key-Tresor + URL-Matcher. Die
  Intelligenz (welche API, welcher Endpoint, welche Query-Syntax) lebt komplett im
  Markdown-Skill `medical-research.md`, das `fetch_url`-Calls vorschreibt. Wenn man
  "Research kaputt" debuggt, muss man zwischen drei Schichten unterscheiden:
  (1) Skill liefert dem Agenten die richtigen URLs, (2) `fetch_url` injiziert Auth,
  (3) Registry liefert den Key. Die meisten Quellen sind keyless → Schicht (3) ist oft
  gar nicht beteiligt.

- **Override-only-Persistenz ist die zentrale Invariante.** Persistiert werden nur
  `key` und `enabled` (`_OVERRIDE_FIELDS`). Wenn man im Seed eine `base_url` oder ein
  `url_pattern` ändert, gilt das sofort für alle — ein bereits gespeicherter Override
  überschreibt nur Key/Enabled, nie das Pattern. Das ist gewollt: Seed = Code = SSOT für
  Struktur, JSON = nur Admin-Geheimnisse/Schalter. **Falle:** ändert man eine SEED-`id`,
  verwaisen bestehende Overrides still (kein Match mehr in `_set_override`/Merge), der Key
  ist "weg" (bleibt verschlüsselt im JSON liegen, wird aber nie mehr gemerged).

- **`match_research_api` greift nur als *zweite* Auth-Quelle.** `_select_cred` priorisiert
  per-User-Credentials. Und: ein **explizit erzwungenes** `auth_name` schaltet den
  Registry-Fallback komplett ab (auch wenn das Profil nicht auflöst → dann `None`, kein
  Key). Das verhindert, dass ein vom User gewähltes (falsches) Profil heimlich durch einen
  System-Key ersetzt wird. Getestet in `test_select_cred_precedence`.

- **"Erstes Match gewinnt" ist nicht spezifisch.** `match_research_api` iteriert `list_apis()`
  in Seed-Reihenfolge und nimmt das erste passende `url_pattern`. Bei sich überschneidenden
  Patterns (aktuell keine im Seed) wäre die Reihenfolge im SEED-Array ausschlaggebend.

- **Keyless/disabled → `None`, kein Key injiziert.** `match_research_api` überspringt
  Quellen ohne `key`, ohne `enabled`, oder mit `auth_type=none`. Für die ~10 keyless
  Quellen passiert also nie eine Injektion — `fetch_url` ruft sie einfach roh ab. Das ist
  korrekt und gewollt (PubMed & Co. brauchen keinen Key).

- **Key-Verschlüsselung teilt sich den Master-Key mit dem Credential-Store.** Beide nutzen
  `credentials/_crypto.py` (AES-GCM, Master-Key aus `HH_MASTER_KEY` env oder
  `data_dir/credentials/.master_key`). Geht der Master-Key verloren/rotiert, werden **alle**
  Research-Keys un-entschlüsselbar — `_load_overrides` fängt das ab (Warnung + Key gedroppt,
  `enabled`-Override bleibt), aber die Quelle ist dann effektiv keyless/tot bis neu eingegeben.
  Getestet in `test_load_overrides_tolerates_undecryptable_key`.

- **`needs_key` und `polite_email_param` sind reine Daten-/UI-Felder.** Kein Backend-Code
  liest sie. `needs_key` steuert nur das Frontend-Badge; die echte "ohne Key tot"-Semantik
  ergibt sich allein aus `enabled=False` im Seed (CORE, ICD-11 starten disabled). Ändert man
  `needs_key` ohne `enabled`, ändert sich am Verhalten nichts. `polite_email_param`/`mailto`
  ist dokumentiert, aber **nicht implementiert** — niemand hängt automatisch ein `mailto`
  an OpenAlex/Crossref-Requests an; der Polite-Pool-Vorteil wird also gar nicht genutzt.

- **Der Reachability-Test umgeht den SSRF-Schutz.** `test_api` ruft `httpx.get(base_url)`
  direkt, nicht über `safe_async_client`. Da `base_url` aus dem (admin-kontrollierten) Seed
  kommt und nicht user-gesteuert ist, ist das Risiko begrenzt — aber es ist eine bewusste
  Inkonsistenz gegenüber dem gehärteten `fetch_url`-Pfad. Der Test injiziert auch **keinen**
  Key, prüft also nur Erreichbarkeit der Basis-URL, nicht die Key-Gültigkeit. `ok` heißt
  "Server antwortet mit <500", nicht "Key funktioniert".

- **Alle Endpoints admin-only.** Bewusst: die Registry ist system-weit geteilte
  Recherche-Infra (Kommentar in der Route nennt die "LLM-Seite" als Vorbild). Normale User
  können Keys weder sehen noch setzen. Das Frontend zeigt bei 403 einen Fallback-Text.

- **Atomarer Write + 0600.** `_save_overrides` schreibt `.json.tmp` und `replace`t, dazu
  `chmod 0600` — Standard-Härtung für eine Datei mit (verschlüsselten) Secrets. Der
  `os.chmod` schluckt `OSError` (z.B. auf FS ohne POSIX-Perms).

- **Lazy Import in `fetch_url`.** `match_research_api` wird erst zur Laufzeit importiert
  (`fetch_url.py:76`), nicht modul-top-level — vermeidet zirkuläre Imports (research → credentials → …)
  und das `settings.data_dir`-Freeze-Problem (siehe Memory: Imports lazy halten).

---

## Datenmodell

### Dataclass `ResearchApi` (in-memory, aus Seed+Override gemerged)
| Feld | Typ | Override? | Konsumiert von |
|------|-----|-----------|----------------|
| `id` | str | nein (Key) | alles |
| `name` | str | nein | Frontend |
| `category` | str (CATEGORIES) | nein | Frontend-Gruppierung |
| `base_url` | str | nein | `test_api` Reachability |
| `url_pattern` | str (Glob) | nein | `match_research_api`/`matches_url` |
| `docs_url` | str | nein | Frontend-Link |
| `description` | str | nein | Frontend |
| `needs_key` | bool | nein | **nur Frontend-Badge** |
| `auth_type` | str (AUTH_TYPES) | nein | `match_research_api`/`_apply_auth` |
| `auth_param` | str | nein | `match_research_api` (header/query-Name) |
| `polite_email_param` | str | nein | **toter Code (nicht konsumiert)** |
| `rate_limit` | str | nein | Frontend-Text |
| `enabled` | bool | **ja** | `match_research_api`, Frontend |
| `key` | str (Secret) | **ja** (verschlüsselt) | `match_research_api`, `_apply_auth` |

### Persistenz-Datei: `research_apis.json`
- Pfad: `settings.config_dir / "research_apis.json"` (via `settings.research_apis_config`).
- Format: `{ "<id>": { "key": "enc:v1:…", "enabled": true|false }, ... }` — **nur** Overrides, nur die 2 Felder.
- Keys: AES-GCM-verschlüsselt mit Präfix `enc:v1:` (base64url von nonce+ciphertext).
- Perms: `0600`, atomarer Write via `.json.tmp`.
- Legacy: Plaintext-Keys werden beim nächsten Write automatisch verschlüsselt (siehe `_crypto.decrypt` no-op bei fehlendem Präfix).

### Master-Key (geteilt mit Credential-Store)
- Quelle 1: env `HH_MASTER_KEY` (64 Hex = 32 Byte).
- Quelle 2: `data_dir/credentials/.master_key` (auto-generiert, `0600`).

### `public_dict()`-Antwort (Frontend/GET)
Alle Felder oben **außer** `key`, **plus** `has_key: bool`.

### API-Antworten
- `GET /api/research-apis` → `{"apis": [ResearchApiPublic, …]}`.
- `PATCH /api/research-apis/{rid}` → `ResearchApiPublic` (oder 404 `"unknown research api"`).
- `POST /api/research-apis/{rid}/test` → `{"ok": bool, "status": int}` oder `{"ok": false, "error": str}` (oder 404).

### Env-Vars
- `HH_MASTER_KEY` — optionaler Master-Key (sonst File-Fallback). Nicht research-spezifisch, geteilt.

### Skill-Frontmatter (`medical-research.md`)
- `name: medical-research`, `tools_required: [fetch_url]`, plus `description`/`when_to_use` (für Skill-Auswahl durch den Agenten).

---

## Offene Enden

- **`ResearchApisView` ist verwaist / nicht gemountet.** Die Komponente
  (`ResearchApisView.tsx:125`) wird **nirgendwo** importiert oder gerendert — kein Eintrag in
  `HealthPage.tsx`, `HealthSidebar.tsx` oder einer Route. Sie liegt im `health/views/`-Ordner,
  aber es gibt keine Navigation dorthin. Der Backend-Endpoint, der API-Client und die Tests
  existieren vollständig, **aber der Admin kann die Forschungs-APIs aktuell gar nicht über die
  UI konfigurieren** (nur per direktem PATCH-Call). Klassischer "gebaut, aber nie verdrahtet"-Fall
  (vgl. RA-6-Commit `d7e87d64` erstellte die View, der spätere Redesign-Commit `f63014af`
  hat sie offenbar nicht ins neue `.box`-Navigationsgerüst übernommen). Kandidat für
  "tot → raus oder wire" nach Tills Cleanup-Regel.

- **`polite_email_param` / `mailto` ist totes Daten-Feld.** Im Modell und Seed gepflegt
  (OpenAlex/Crossref), aber **kein Code** hängt jemals ein `mailto` an Requests. Der
  versprochene Polite-Pool-Vorteil ("mit mailto = schneller") wird nicht eingelöst.
  Entweder in `match_research_api`/`fetch_url` implementieren oder das Feld entfernen.

- **`needs_key` ist semantisch redundant.** Backend leitet "ohne Key nutzbar?" allein aus
  `enabled`/`key` ab; `needs_key` ist nur ein UI-Badge. Inkonsistenz-Risiko: man kann eine
  `needs_key=True`-Quelle (CORE) im Frontend auf `enabled` toggeln **ohne** Key zu setzen —
  dann ist sie aktiv, aber `match_research_api` liefert mangels `key` trotzdem `None`, der
  Agent bekommt 401/403. Das Skill dokumentiert genau diesen Fall ("Bei 401/403 … keine
  keyless Alternative"), aber die UI verhindert das Toggeln-ohne-Key nicht.

- **Reachability-Test ohne SSRF-Schutz und ohne Key.** `test_api` nutzt nacktes `httpx.get`
  statt `safe_async_client` (Inkonsistenz zum gehärteten `fetch_url`) und prüft nur
  HTTP-Erreichbarkeit der `base_url`, nicht ob der hinterlegte Key gültig ist. Ein "OK (200)"
  kann trotz falschem/fehlendem Key erscheinen → irreführend für den Admin.

- **Seed-Header sagt "15 Quellen", Test fordert nur `>=12`.** Kein echter Bug, aber der
  Test ist laxer als die Realität; eine versehentliche Halbierung des Seeds würde nicht
  auffallen.

- **ICD-11 OAuth ist nur ein manueller Bearer-Workaround.** `icd11` braucht eigentlich
  OAuth-Client-Credentials-Flow; in "v1" muss der Admin manuell einen kurzlebigen Bearer-Token
  als Key eintragen (Seed-Description + Skill sagen das). Es gibt **keine** Token-Refresh-Logik
  — der Token läuft ab und die Quelle wird still tot (`401`), bis jemand manuell nachträgt.
  Bekannte, dokumentierte Halbfertig-Stelle.

- **`url_pattern`-Matching ist ein simpler Glob.** `matches_url` übersetzt nur `*` → `.*`.
  Keine Pfad-Normalisierung, kein Schema/Host-Splitting. Bei künftigen, überlappenden Patterns
  könnte "erstes Match in Seed-Reihenfolge" unerwartet greifen.

- **Kein Audit-/Logging-Eintrag bei Key-Injektion in dieser Schicht.** `_apply_auth` liefert
  zwar einen `auth_hint` fürs Logging zurück, aber ob/wo der landet, hängt am `fetch_url`-/
  Tool-Loop-Logging, nicht an der Research-Registry. Die Registry selbst loggt nur Defekte
  (kaputtes JSON, un-entschlüsselbarer Key).
