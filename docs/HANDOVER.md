# HydraHive2 — Übergabe (Stand 2026-05-10)

Konsolidierter Snapshot. Beim Wieder-Aufnehmen diese Datei zuerst,
dann SPEC.md, dann konkret nach offenen Tasks fragen.

---

## Aktueller Stand (2026-05-10, Tag 2 nach 05-09-Pause)

- **Tests:** 264/264 grün (+21 vs. gestern: +8 Voice, +3 vms-route-order, +10 disk_interface).
- **Tag-2-Sweep** (2026-05-10): Update-Modal-Fix, HA Voice Phase 1 Backend,
  zwei Kunden-Bugs gefunden + behoben (vms-Routing 404, qcow2-Boot-Mismatch).
  Siehe Sektion unten.
- **Phase-D Memory-Diagnose abgeschlossen:** alle Smells S1–S4 jetzt geschlossen
  (#113–#116, siehe Memory-Smells-Sektion unten).
- **Token-Verbrauch beim longterm_memory-Agent halbiert** — Live-gemessen
  und bestätigt, siehe Token-Sektion.
- **Phase-E Architektur-Audit:** 4 parallele Audit-Agents (Backend Core /
  Backend Data / API+Auth / Frontend) durchgekämmt. 3 echte Bugs sofort
  gefixt (S5, S3, B5), 7 Backlog-Issues angelegt (#117–#123).
- **Phase-F Doku-Pyramide:** Stale-Content aufgefrischt, 4 Architektur-
  Subsystem-Docs angelegt, README/docs-Lesepfad aufgebaut. Siehe Doku-
  Sektion unten.

---

## ✅ Token-Verbrauch beim Projekt-Agenten (Status: behoben + verifiziert)

**Vorgeschichte:** Sonnet-4-6-Agent mit `longterm_memory=true` hat für eine
einzelne User-Frage 11 Iterationen + 16 `datamining_search`-Calls (14× count=0)
abgefeuert — Brute-Force durch Query-Synonyme.

### Drei Root-Causes (Live-Test Session `019e0d9a`, Sonnet 4-6, 2026-05-09)

1. **Pflicht-Prompt zu aggressiv** — `_LONGTERM_MEMORY_PROMPT` befahl "rufe
   ZUERST datamining_search bei jeder Frage" → Agent hat auch bei generischen
   Fragen gesucht.
2. **Loop-Detection blind für Query-Variationen** — Agent variiert Synonyme
   (`"admin Buddy"` → `"admin Buddy session Thema"` → `"Bookstack Mailcow"`),
   keine zwei Calls sind identisch. Loop-Schutz greift nicht.
3. **datamining_semantic verschwendet** — wird unkonditional registriert auch
   wenn `embed_model` leer ist → Tool-Call schlägt mit "Embedding fehlgeschlagen"
   fehl, kostet Tokens für nichts.

### Drei Fixes (Commit `71dc30f`, `core/src/hydrahive/runner/_runner_setup.py`)

- **A:** Prompt entschärft: "Nutze sie wenn die Frage konkret auf etwas
  Vergangenes verweist" statt "rufe ZUERST".
- **B:** Empty-Search-Budget eingeführt: "wenn zwei aufeinanderfolgende
  `datamining_search`-Calls `count: 0` zurückgeben, hör auf weitere
  Query-Variationen zu probieren."
- **C:** `inject_longterm_memory` registriert `TOOL_SEMANTIC` nur wenn
  `embed_model` in der LLM-Config gesetzt ist.

### Live-Vergleich (gleiche Frage, gleicher Agent, hh2-218)

| Metrik | Baseline (vor Fix) | Nach Fix | Δ |
|---|---|---|---|
| Iterationen | 11 | **6** | −45% |
| Tool-Calls | 16 (14× leer) | **7** (4× leer) | −56% |
| Input-Tokens | 9 591 | 8 388 | −13% |
| Output-Tokens | 2 701 | 1 384 | −49% |
| Cache-Create | 48 004 | 18 750 | −61% |
| Cache-Read | 132 558 | 69 560 | −48% |
| **Total** | **192 854** | **98 082** | **−49%** |

Verhalten verifiziert: Iter 1 startet jetzt mit `datamining_timeline`
statt search-Brute-Force, Iter 5 trifft 2× count=0, Iter 6 stoppt mit
"Okay, ich stopp mit dem Suchen". Empty-Search-Budget greift.

### Frühere Mitigation (bleibt aktiv)

`tool_result_max_chars` (Default 12 000 Zeichen) in dispatcher.py kürzt jedes
Tool-Result bevor es in den Context geht. Per-Agent konfigurierbar in den
Compaction-Settings. Commit: `6d1ff0e`.

---

## ✅ Memory-Smells aus Phase-D (#113–#116, alle behoben)

Alle vier in einer Session 2026-05-09 abgeräumt — UI-Section live auf hh2-218
verifiziert.

### #114 — Re-Crystallize einer Session unmöglich (`b6afef6`)
`crystals.jsonl` ist jetzt **append-only versioniert**:
- `crystallize_session(force=True)` springt am `existing`-Check vorbei und
  schreibt einen neuen Crystal. Alter Eintrag bleibt im File.
- `get_crystal()` liefert den neuesten Match per `session_id`.
- `list_crystals()` dedupliziert per `session_id` (last-write-wins).
- `_iter_entries()` Helper konsolidiert das JSONL-Lesen.
- 11 neue Tests (`test_crystallize_storage.py`).

### #116 — `_save_lessons` N×Memory-Rewrite (`9ee6631`)
Analog zu `mark_compressed_bulk` aus Phase D (`6fcd6fb`):
- `_apply_write()` extrahiert die pure Mutation auf `MemoryStore`-Dict ohne IO.
- `write_keys_bulk(entries)` macht ein File-Read+Write für die ganze Batch.
- `write_key()` unverändert; `_save_lessons()` nutzt jetzt Bulk.
- 9 neue Tests (`test_memory_bulk.py`).

### #115 + #113 — Per-Agent Memory-Settings + Crystal-Scope (`372b01f`)
Bündel-PR weil beide am `build_memory_context()`-Code-Pfad hängen.

**5 neue Agent-Config-Felder** (Defaults wie bisher, alle backfillen via
`normalize()`):
- `memory_max_crystals: int = 5`
- `memory_max_lessons: int = 10`
- `memory_min_lesson_confidence: float = 0.6`
- `memory_max_chars: int = 4000`
- `memory_crystal_scope: "project_and_global" | "project_only"` ← #113

**Designentscheidung #113:** Default ist **`project_and_global`** — ein
Project-Agent sieht jetzt sowohl seine eigenen Crystals als auch globale
(`project=None`) vom Master-Buddy. Konsistent mit Lessons-Verhalten. Wer
strikte Isolation will, schaltet auf `project_only`.

**Frontend:** neue `MemorySection.tsx` auf dem Advanced-Tab unter
`CompactionSection`. 5 Felder + i18n DE/EN.

**Backend-Änderungen:**
- `_defaults.py`: 5 `DEFAULT_MEMORY_*`-Konstanten
- `_config_utils.normalize`: Backfill für bestehende Agents
- `_agent_schemas.py`: 5 neue Felder in `AgentCreate` + `AgentUpdate`
- `_context_injection.build_memory_context(*, agent_config=None)`
- `_crystallize_storage.list_crystals(include_global=False)` Param
- `runner.py`: agent-Dict an `build_memory_context` durchreichen

**Tests:** 12 neue (`test_memory_context_injection.py`) für Defaults, alle
4 Threshold-Overrides, alle 3 Scope-Modi.

### Aggregat dieser Session
4 Commits (`b6afef6`, `9ee6631`, `372b01f` + `66f2336` HANDOVER-Update),
Tests von 197 → 229 (+32), ruff clean, tsc clean.

---

## ✅ Phase-E Architektur-Audit (2026-05-09)

Vollständiger Sweep mit 4 parallelen Explore-Agents über Backend-Core
(Runner/Tools/LLM), Backend-Data (DB/Settings/Communication), API+Auth+Agents,
und Frontend.

### Re-Bewertung der Audit-Findings

Audits sind grobes Sieb — von 11 gemeldeten Sicherheits-/Bug-Findings waren
nach Code-Review **3 echte Bugs**, **2 sind by-design** (Admin-only Endpoints
sollen Admin-only sein), und **6 sind Hardening- oder Smell-Themen** für
später.

### Sofort gefixt (3 Commits, gepusht)

| # | Commit | Fix |
|---|---|---|
| **S5** | `0156cad` | `get_current_user_optional()` schluckte alle Exceptions stumm — jetzt `logger.debug` mit Fehler-Repr. Verhalten unverändert, nur Diagnose-Pfad ergänzt. |
| **S3** | `b62108a` | OAuth-Token-Refresh war read-modify-write auf `llm.json` ohne Lock. Race zwischen API-Server + Web-UI konnte einen Refresh überschreiben → Logout. Neuer `oauth/_llm_config_rmw.py` mit `fcntl.flock` + atomic write (temp+rename). 6 neue Tests inkl. multiprocessing-Concurrency-Test. |
| **B5** | `a655deb` | Non-Streaming-Fallback in `_call.py` verlor Token-Counts (alle 4 = 0 in metadata). Streaming-Pfad war OK. Neuer Helper `runner/_token_usage.py`, alle 3 LLM-Backends + `codex_call` + `call_with_tools` returnen jetzt `(blocks, stop_reason, usage)`. 8 neue Tests. |

### Als Issues angelegt

| # | Schwere | Was |
|---|---|---|
| **#117** | Hardening | Encrypted-at-Rest für Credentials (AES-GCM + Master-Key-Konzept) |
| **#118** | Hardening | API-Key linear-bcrypt-Loop ersetzen durch key_id-Lookup |
| **#119** | Bug (klein) | `db/state.py` `json.loads` ohne Fallback bei korrupter Row |
| **#120** | Bug (klein) | Race in `db/sessions.set_model_override` (RMW ohne Tx) |
| **#121** | Bug (klein) | `tools/_observations` JSONL-Append ohne fcntl-Lock |
| **#122** | Smell | Fire-and-forget `asyncio.create_task` in compress-Trigger ohne Exception-Handler |
| **#123** | Bundle | A1-A5: Files nahe 250er-Limit, OAuth-Dedup, N+1, tool_confirmation, API-Konsistenz |

### Audit-Methodik (für nächstes Mal)

- 4 parallele Agents nach Subsystem trennt sauber
- Findings nicht blind übernehmen — kritisch hinterfragen vor Fix
- Test-Coverage für Race-Conditions: `multiprocessing.Process` × N für echte Concurrency (das was `flock` testen muss)

### Aggregat
3 Commits (`0156cad`, `b62108a`, `a655deb`), Tests von 229 → 243 (+14).
Frontend war sauber — Spot-Check der heutigen MemorySection bestätigte
i18n-Konsistenz und Feature-Folder-Pattern.

---

## ✅ Phase-F Doku-Pyramide (2026-05-09)

Drei-Phasen-Sweep um die Doku auf den aktuellen Stand zu bringen und
einen klaren Lesepfad pro Audience aufzubauen.

### Phase 1 — Stale-Content (`be3967d`)

- **TESTING_STATUS.md** komplett umgeschrieben: 60 → **243 Tests**,
  Coverage-Matrix pro Subsystem (alle Kern-Subsysteme jetzt 🟢), CI-Job-
  Beschreibung mit ruff+tsc, offene Lücken klar (MCP-Mock, AgentLink, E2E).
- **STRUCTURE.md** Header-Stats aktualisiert (343 .py, 262 .ts/.tsx, 17
  Test-Files).
- **TEST_DEEP_DIVE.md** + **TEST_CHECKLIST.md** als historisch markiert mit
  Banner — "0 Tests"-Schock-Doku vom 2026-05-06 sollte niemand mehr für den
  aktuellen Stand halten.
- **CONTRIBUTING.md** erweitert: Commit-Konventionen mit Beispielen,
  Test-Naming + Race-Tests via multiprocessing, Code-Konventionen
  (Atomic Writes mit flock, Lazy-Import, File-Größen).

### Phase 2 — Architektur-Subsystem-Docs (`8ecee01`)

Neuer Ordner `docs/architecture/` mit 4 Deep-Dives + Index. Ziel: Onboarding
ohne dass man 343 .py-Files lesen muss.

| Doc | Zeilen | Was |
|---|---|---|
| `memory.md` | 128 | Pipeline Observation→Compress→Crystallize→Lessons→Injection. Per-Agent-Settings, Crystal-Scope (#113), Append-Only-Versioning (#114), Bulk-Writes (#116/B1), Empty-Search-Budget. |
| `runner.md` | 149 | Tool-Loop pro Iter, Streaming vs Fallback, 4 Provider-Backends, Token-Counts in beiden Pfaden (B5), Stop-Reason-Behandlung. |
| `compaction.md` | 134 | OpenClaw-Pattern firstKeptEntryId-Pointer, hierarchisches Merging bei multi-window Historie, Secret-Redaction, Plugin-Hooks. |
| `auth.md` | 187 | JWT vs API-Key, Roles, Login-Lockout, OAuth-Flow für Anthropic + ChatGPT Plus/Pro, atomic Refresh via flock (S3-Fix). |
| `README.md` | 24 | Index + Pflege-Hinweise. |

### Phase 3 — Onboarding-Pfad (`433bd86`)

- **`docs/README.md`** als Doku-Index sortiert nach Audience: nutzen /
  beitragen / verstehen / Tests / KI-Session aufgreifen. Gibt jedem
  Einsteiger die Lese-Reihenfolge vor.
- **`README.md`** neue Sektion "Dokumentation" mit Tabelle "Du willst X →
  lies Y". Vorher waren 3 Links unten ohne Pfad — jetzt klare Hierarchie.

### Aggregat
3 Commits (`be3967d`, `8ecee01`, `433bd86`), 884 Zeilen Doku-Delta
(622 neu in `architecture/` + 200 refresht + 57 README/Index + 5 STRUCTURE).
Code unverändert, alle Tests grün.

---

## ✅ Tag-2-Sweep (2026-05-10)

Sechs Commits in einer Session — Update-Hänger gefixt, Voice-Phase-1
gebaut, zwei Kunden-Bugs unter Druck gefunden und sauber behoben (mit
SPEC + Tests, nicht als Hand-Patch).

### Update-Modal-Hänger (`2818a6d`)

Problem: bei einem Klick auf "Update" wenn der Server schon auf neuestem
Stand ist (`git pull` → "Bereits aktuell"), blieb das Modal 5 Min auf
"Update läuft…". Frontend wartete in `useLayoutUpdate.ts` aussschließlich
auf einen **commit-change** in `/api/health` — der nie kommt.

Fix in `frontend/src/shared/useLayoutUpdate.ts`:
1. **Pre-Check**: vor dem POST-Trigger frischer `/api/system/check-update`,
   wenn Server schon "behind=0" sagt → direkt "done", kein Update-Trigger.
2. **Server-Stable-Fallback**: im Polling-Loop einen Counter — wenn
   `/api/health` 15s lang stabil mit unverändertem Commit antwortet
   (Server ist nach Restart wieder erreichbar, kein neuer Commit in
   Sicht), gilt das Update als done. Counter resettet bei Errors damit
   der Service-Restart-Zeit nicht falsch positiv wertet.

### HA Voice Phase 1 (`d00d7fc` + `37110ad`)

**SPEC** als Standalone-Commit zuerst (`d00d7fc`): neue Sektion "Home
Assistant — Conversation Agent" nach Voice. HydraHive antwortet als
Conversation-Agent in HA's Voice-Pipeline (Voice-PE-Pucks etc.) — kein
Bezug zum internen Whisper-Stack, HA macht STT/TTS selbst.

**Code** (`37110ad`):
- `core/src/hydrahive/api/routes/voice.py` — `POST /api/voice/chat`,
  Auth via API-Key (`hhk_*`) oder JWT, Owner-Check auf den Agent
- `core/src/hydrahive/voice/_ha_conversation.py` — Mapping
  HA-`conversation_id` → HydraHive-Session in `voice_conversations.json`,
  atomic write, FIFO-Cleanup bei >1000 Einträgen
- Runner-Loop mit 25s-Timeout, Tool-Calls werden serverseitig
  abgearbeitet, nur finaler Text-Block geht an HA zurück
- 8 Tests in `test_voice_chat.py`, plus shared TestClient-Fixtures aus
  `test_api_integration.py` nach `conftest.py` verschoben

**Phase 2 (HA Custom Component)** und **Phase 3 (Doku)** stehen aus.
Phase 2 ist der nächste logische Schritt — der Endpoint nützt nichts
ohne HA-Bridge. Geschätzt 200-300 Zeilen Python für `manifest.json`,
`config_flow.py`, `conversation.py` mit der modernen `ConversationEntity`-
API plus de/en Translations.

### Kunden-Bug 1: VMs-Routing 404 (`1d921c6`)

**Symptom (Kunde, Server `192.168.178.86`)**: Import-Jobs-Panel zeigt nie
einen Job, kurz erscheint "VM nicht gefunden". Frontend pollt
`/api/vms/import-jobs` → 404 `vm_not_found`. Backend ist auf neuestem
Stand, Route ist registriert.

**Cause**: in `vms.py` wird `_lifecycle_router` (mit `GET /{vm_id}`) VOR
`_imports_router` (mit `GET /import-jobs`) eingebunden. FastAPI matcht
in Definitions-Reihenfolge → `/api/vms/import-jobs` läuft auf
`/{vm_id}` mit `vm_id="import-jobs"`, `vm_or_404` schlägt fehl → 404.
Gleiches Risiko für `/api/vms/isos/list` etc.

**Fix**: Sub-Router mit literalen Pfaden (`imports`, `isos`) VOR den
`/{vm_id}`-Subs einbinden. 3 Regression-Tests in
`test_vms_route_order.py` prüfen Reihenfolge in `app.routes` plus
End-to-End dass GET `/api/vms/import-jobs` und `/api/vms/isos/list`
200 statt 404 liefern.

### Kunden-Bug 2: qcow2-Boot bricht mit virtio (`8c72bd6` + `2342a06`)

**Symptom (selber Kunde)**: Importierte qcow2 vom alten HydraHive 1
(Gast-OS: BSD/macOS/altes), VM startet, BIOS POSTet, Boot-Menü zeigt
die Disk — sobald Bootloader übernimmt, "no bootable device".

**Cause**: `qemu_args.py` hängte die Disk hart als `if=virtio` an. Der
Bootloader im Image hat keinen virtio-Treiber — SeaBIOS sieht die Disk
zwar (deshalb Boot-Menü-Eintrag) aber sobald der MBR/UEFI-Bootloader
geladen ist, ist die Disk für ihn unsichtbar.

**Spec-Update standalone** (`8c72bd6`): VM-Sektion erweitert um
"Disk-Interface pro VM wählbar: virtio (Default), sata (kompatibel,
für importierte Images), ide (Notnagel)".

**Code** (`2342a06`):
- Migration `008_vm_disk_interface.sql` — `ALTER TABLE vms ADD COLUMN
  disk_interface TEXT NOT NULL DEFAULT 'virtio'`. Bestehende VMs
  behalten Verhalten.
- `vms/models.py` — neuer Literal `DiskInterface = "virtio"|"sata"|"ide"`,
  Default `virtio` (musste hinter alle non-default-Felder verschoben
  werden — Dataclass-Reihenfolge)
- `vms/qemu_args.py` — neue `_disk_args(vm)`-Funktion, branched auf
  `vm.disk_interface`. sata baut `-drive if=none,id=disk0` + `-device
  ahci` + `-device ide-hd,bus=ahci.0,drive=disk0`. ide ist klassisches
  `-drive if=ide`.
- `_vm_lifecycle_schemas.py` + `vms_lifecycle.py` — VMCreate/VMUpdate
  akzeptieren `disk_interface`, Validation gegen `DISK_INTERFACES`,
  400 `vm_disk_interface_invalid` bei unbekanntem Wert.
- Frontend: `types.ts` neue `DiskInterface`, `CreateVMDialog` mit
  3-Wege-RadioCard plus kontextuellem Hinweis bei Boot-Source "Import",
  `EditVMDialog` mit Select + Hinweis "VM stoppen → ändern → starten".
- 10 Tests in `test_vm_disk_interface.py`: Migration-Spalte, Default,
  qemu_args-Branches für alle drei Werte, Create/Patch mit gültigen
  und ungültigen Werten.

### Aggregat Tag 2

6 Commits (`2818a6d`, `d00d7fc`, `1d921c6`, `37110ad`, `8c72bd6`,
`2342a06`), Tests **243 → 264** (+21), alle grün, frontend tsc + ruff
clean. SPEC zwei standalone-Commits (HA-Voice + disk_interface), beide
mit Pre-Commit-Hook-Compliance.

---

## Diese Session (2026-05-06, Nacht)

### 3 Security-Fixes (alle committed & auf hydratest deployed)

**#104 — SSRF-Schutz in http_request Tool**
- `tools/http_request.py`: IP-Blocking für alle privaten/link-local Ranges
  (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16,
  IPv6 loopback/private). Öffentliche IPs + Hostnamen laufen durch.
- Commit: `b1efd45`

**#102 — /api/files Auth-Header**
- `api/routes/files.py`: Cookie-based Fallback-Auth (`hh_file_token`) für
  Browser-img-src die kein Bearer-Header schicken können.
- `api/middleware/auth.py`: `get_current_user_optional()` Hilfsfunktion ergänzt.
- Commits: `265513f`, `69ca0f7`

**#100 — Butler-Webhook-Secret**
- `projects/config.py`: `webhook_secret` (secrets.token_urlsafe(32)) bei jedem
  neuen Projekt automatisch generiert.
- `api/routes/butler.py`: Webhook-Endpoint prüft `X-Webhook-Secret`-Header,
  constant-time compare mit `hmac.compare_digest`.
- `butler/models.py`: `webhook_secret`-Feld ergänzt.
- Commit: `c961c9e`

### hydratest — neue Dev-Instanz

**IP:** 192.168.3.23 (Incus-Container `hydratest` auf dem lokalen Host)
**Zugriff:** `incus exec hydratest -- <command>` (als root)
**URL:** https://192.168.3.23/ (Self-Signed Cert → Browser-Warning normal)
**Login:** admin / u1BdpQJPMKGyy6py5413HA

Installiert per `./install.sh` — kein einziger manueller Schritt notwendig,
Installer hat alles in ~4 Minuten aufgesetzt. 0 Bugs beim Frisch-Install.

Specs: Ubuntu 24.04 LTS, 31 GB RAM, 12 CPU, 1.8 TB Disk.

**Zweck:** Saubere Test-Instanz für Security-Fixes und neue Features.
Die 218er-Instanz bleibt Produktiv-Test (Tills Daily-Driver).

### tool_result_max_chars (Live-Truncation)

Neues per-Agent-Feld. Geänderte Dateien:
```
core/src/hydrahive/agents/_defaults.py          DEFAULT_TOOL_RESULT_MAX_CHARS = 12_000
core/src/hydrahive/agents/_config_utils.py      normalize() backfill + Import
core/src/hydrahive/runner/dispatcher.py         to_tool_result_block() kürzt
core/src/hydrahive/runner/runner.py             liest max_chars, reicht weiter
core/src/hydrahive/api/routes/_agent_schemas.py API-Schema AgentCreate + AgentUpdate
frontend/src/features/agents/CompactionSection.tsx  neues Dropdown (0/4k/8k/12k/20k/50k)
frontend/src/features/agents/types.ts           tool_result_max_chars?: number
frontend/src/i18n/locales/de/agents.json        live_truncation i18n-Keys
frontend/src/i18n/locales/en/agents.json        live_truncation i18n-Keys
```

---

## Offene Issues (Stand nach dieser Session)

| # | Titel | Labels | Status |
|---|-------|--------|--------|
| 75 | Member-Rechte: Read/Write/Admin pro Member | p3, enhancement | offen |
| 74 | Audit-Log pro Projekt | p3, enhancement | offen |
| 65 | Files-Tab: Edit + Save + Upload + Delete | p3, enhancement | offen |
| 47 | Chat-Suche (Strg+F) | p3, enhancement | offen |
| 44 | Branching/Tree-View | p3, enhancement | offen |
| 37 | Matrix-Channel-Adapter | p3, enhancement | offen |
| 36 | Telegram-Channel-Adapter | p3, enhancement | offen |
| 32 | PostgreSQL: SPEC vs. Code | p3, architecture | offen — Doku-Task |
| 15 | ZH-Locale fehlt | p3, architecture | offen — Nice-to-have |

Alle geschlossen: #104, #102, #101, #100, und alle früheren Issues.

**#101 (pgvector silent failure):** Gefixt am 2026-05-07 in `9a940ce` —
apt-cache check vor Install, klare WARNUNG mit Fix-Hinweis statt stillem `||`,
Extension-Health-Check am Ende mit konkretem psql-Befehl. Bewusst tolerant
(nicht fail-fast), damit Installer ohne pgvector durchläuft.

---

## Bisheriger Stand (aus vorheriger Übergabe, unverändert)

### Codex-Modelle Live-Validierung
- 9 Codex-Modelle gepflegt (Frontend + Catalog + Installer)
- Empirisch geprüft: nur gpt-5.5, gpt-5.4, gpt-5.3-codex, gpt-5.2 funktionieren
- `CodexModelNotAllowed` in `_codex_provider.py`, sprechende Fehlermeldung in UI

### Effort-Pill im Chat-Header (pausiert)
- Backend-Mapping fertig (low=1k, medium=4k, high=16k Tokens)
- Frontend fehlt noch: Pill, Persistenz in session.metadata, API-Schema

### MiniMax OAuth (pausiert)
- API-Key reicht aktuell

### Backlog
- Telegram + Matrix-Adapter
- Branching/Tree-View in Chat
- Bundle-Splitting (#95)
- DB-Indizes (#96)
- MCP-Datamining-Server deployen + als Tool einbinden
- Mehr NVIDIA-Modelle in Metadata-Tabelle (aktuell ~25 von 121)

---

## Installer / Server

### Test-Server 218 (chucky@hh2-218 / 192.168.178.218)
- LXC-Container auf TrueNAS, kein /dev/kvm
- Repo: `/opt/hydrahive2`, Service-User: `hydrahive`
- Update-Trigger: `sudo touch /var/lib/hydrahive2/.update_request`
- **Wichtig:** Security-Fixes noch nicht auf 218 deployed (nur auf hydratest)

### hydratest (192.168.3.23)
- Incus-Container, root-Zugang via `incus exec hydratest -- ...`
- Fresh-Install vom heutigen Stand
- Security-Fixes #104, #102, #100 drauf, getestet

---

## Wichtige Lektionen (neu diese Session)

- **Tool-Results ohne Limit = Token-Bombe**: Ein einziger `gh issue list` mit
  100+ Issues als JSON frisst ~13k Token. Ab jetzt: tool_result_max_chars.
- **Projekt-Agent mit Longterm-Memory ist teuer**: Datamining-Calls am
  Session-Start plus große Tool-Outputs summieren sich brutal schnell.
- **Token-Verbrauch immer im Auge behalten**: Nach dem Fix auf hydratest testen
  ob 12k Limit ausreicht oder weiter gesenkt werden muss.
