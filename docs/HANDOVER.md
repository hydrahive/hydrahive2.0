# HydraHive2 — Übergabe (Stand 2026-05-09)

Konsolidierter Snapshot. Beim Wieder-Aufnehmen diese Datei zuerst,
dann SPEC.md, dann konkret nach offenen Tasks fragen.

---

## Aktueller Stand (2026-05-09, Phase-0-Cleanup)

- **Tests:** 197/197 grün lokal + CI (`.github/workflows/pytest.yml` mit Ruff+TSC)
- **Tool-Cleanup vervollständigt** (#112): verwaiste `dir_list/file_search/http_request`
  -Dateien gelöscht, Skills/Frontend/i18n-Help nachgezogen, `e034e07` (verloren
  durch Force-Push) als Pflaster zurückgeholt — Commits `adbb30b` + `01c02b1`.
- **#101 pgvector** seit `9a940ce` (2026-05-07) gefixt.
- **Phase-A Schliff abgeschlossen:** settings/mirror_query/runner/datamining-route
  in <250-Zeilen-Module aufgeteilt (Mixin- + Facade-Pattern).
- **Phase-D Memory-Diagnose abgeschlossen:** B1 (mark_compressed N-Rewrite) +
  B2 (dead crystallize tool) gefixt. Issues #113-116 für Smells S1–S4 angelegt.
- **Token-Verbrauch beim longterm_memory-Agent halbiert** — Live-gemessen
  und bestätigt, siehe nächste Sektion.

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
