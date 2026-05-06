# HydraHive2 — Übergabe (Stand 2026-05-06 nach 04:30 Uhr)

Konsolidierter Snapshot. Beim Wieder-Aufnehmen diese Datei zuerst,
dann SPEC.md, dann konkret nach offenen Tasks fragen.

---

## ⚠️ DRINGEND: Exorbitanter Token-Verbrauch beim Projekt-Agenten

**Was passiert:** Der Projekt-Chat-Agent (Sonnet 4-5) hat in einer ~20-minütigen
Session 31% des 5-Stunden-Rate-Limits verbraucht. Normalerweise wäre das 1–2%.

**Ursachen die identifiziert wurden:**
- Tool-Results hatten keinerlei Größenbeschränkung. Ein einziger `shell_exec`
  (gh issue list) hat 52.244 Zeichen rohes JSON zurückgegeben — allein das
  sind ~13k Token. Eine `dir_list` hat 63.384 Zeichen (2506 Zeilen) geliefert.
- Jedes Tool-Result geht ungefiltert in den LLM-Context und bleibt dort für
  alle folgenden Iterationen (kumulativ!).

**Erster Fix diese Session:**
`tool_result_max_chars` (Default: 12.000 Zeichen) in dispatcher.py eingebaut.
Jedes Tool-Result wird jetzt live auf 12k Zeichen gekürzt bevor es in den
Context geht. Per-Agent konfigurierbar in den Compaction-Settings im Frontend.

**Commit:** `6d1ff0e feat(runner): live Tool-Result-Truncation — tool_result_max_chars`

**Was NOCH NICHT geklärt ist:**
Das Problem könnte tiefer liegen. Der Projekt-Agent hatte Zugriff auf
Datamining-Tools (Langzeit-Gedächtnis) und hat diese exzessiv genutzt.
Mögliche weitere Ursachen die noch nicht untersucht wurden:
- Ist der System-Prompt des Projekt-Agenten deutlich größer als der Buddy-Prompt?
  (Datamining-Block im Longterm-Memory-Modus hängt ~500 Zeichen an)
- Wird die Cache-Nutzung korrekt ausgenutzt? Bei 96k Input-Tokens sollte der
  Großteil gecacht sein — war das der Fall?
- Hat der Projekt-Agent `longterm_memory=true`? Falls ja, werden bei jedem Turn
  automatisch Datamining-Calls gemacht die den Context vergrößern.

**Nächste Schritte:**
1. Projekt-Agenten-Config prüfen: `longterm_memory`-Flag und aktuelle Toolset-Größe
2. Nach dem nächsten Test: Token-Breakdown ansehen (wie viel davon cached?)
3. Falls immer noch zu hoch: `tool_result_max_chars` auf 8.000 oder 6.000 senken
4. Erwägen ob Projekt-Agent `longterm_memory` überhaupt braucht

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

Alle geschlossen: #104, #102, #101 (pgvector-Fix ist noch offen), #100, und
alle früheren Issues.

**Achtung #101 (pgvector silent failure):** Noch nicht gefixt — nur besseres
Error-Logging vorgeschlagen, aber nicht implementiert.

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
