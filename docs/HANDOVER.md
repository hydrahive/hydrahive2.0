# HydraHive2 — Übergabe (Stand 2026-05-01 nachts, AgentLink-Hookup + Compliance-Sprint)

Konsolidierter Snapshot. Beim Wieder-Aufnehmen diese Datei zuerst,
dann SPEC.md, dann konkret nach offenen Tasks fragen.

## TL;DR

Heute zwei große Stücke + viele Polish-Fixes:

1. **AgentLink full integration** (#83) — neues Repo `hydrahive/hydralink`
   als Wrapper für `tilleulenspiegel/agentlink`. Native Installation
   (kein Docker, ChromaDB raus). HydraHive verbindet sich via
   WebSocket-Client mit Future-Map für synchrones await im Tool-Loop.
   `ask_agent` ist nicht mehr Stub. Service-Drop-In macht 218 beim
   Self-Update automatisch scharf. Frontend (Vite/React-SPA) wird auf
   Port 9001 als statischer http.server-Service ausgeliefert; Link
   zum Dashboard ist in der HydraHive-System-Page.

2. **CLAUDE.md-Compliance-Sprint** (Refactor in 4 Häppchen):
   - `routes/vms.py` 406 → 22 Z. Aggregator + 5 Sub-Router
   - `llm/client.py` 297 → 116 Z. + `_config.py` + `_anthropic.py`
   - `PropertiesPanel.tsx` 623 → 43 Z. + 5 Subtype-Form-Files via Registry
   - `api/main.py` 255 → 85 Z. + `lifespan.py` + `version.py`

Plus B1.a System-Backup, Per-Agent Compaction-Settings, Chunked
Compaction für riesen Sessions, Bento-Menü-Farben, iOS-Layout-Fix,
Chat-Bubble-Polish.

## Was steht (alles getestet, live auf 218 + lokal)

| Bereich | Stand |
|---|---|
| **AgentLink (#83)** | hydralink-Repo + native Installer + WebSocket-Client + ask_agent echte Implementation + System-Card + Dashboard-Link |
| **Compaction Chunking (#81)** | Variante B — bei zu großem Verlauf splitten, hierarchisch mergen, verlustfrei |
| **Per-Agent Compact-Settings (#82)** | compact_model / compact_tool_result_limit / compact_reserve_tokens / compact_threshold_pct in AgentForm |
| **Chat-Bubble-Polish (#39)** | Header (Datum/Uhrzeit) + Footer (Tokens/Cache/Modell) + Tool-Dauer + Collapse |
| **Bunte UI (#77)** | Bento-Menü + Top-Bar Quick-Links + PageTitle-Punkt + 3 Action-Buttons in Domain-Farben |
| **System-Backup B1.a** | /api/admin/backup + /restore mit Pre-Validate + Auto-Rollback + tls/-Exclude |
| **iOS-Layout (#80)** | 100vh → 100dvh — Chat-Page rastet beim Initial-Load ein |
| **Compliance-Refactor** | 4 Files >150 Z. gesplittet, alle <150 (mit ~ Toleranz für 161er) |
| Backend-Runner | Tool-Loop, Streaming, Loop-Detection, Heal, Failover, runner.run() |
| DB-Layer | sessions/messages/tool_calls/state/vms/vm_snapshots/vm_import_jobs/containers, append-only-Compaction |
| Voice (komplett) | STT incus-LXC + TTS mmx-CLI + Voice-Mode-Hint |
| WhatsApp | Bridge mit Promise.all, Voice-Eingang/Ausgang, Auto-Reconnect |
| Butler | 4 Phasen — Datenmodell + Executor + ReactFlow-UI + WhatsApp-Hook |
| Container | LXC Phase 1+2+3 — Lifecycle + Browser-Console + Detail-Page |
| VM-Manager | Phase 1-5 — QEMU+KVM, Browser-VNC, Snapshots, Import, Live-Stats |

## Heute gepusht (Reihenfolge chronologisch, Auswahl)

```
4755135 fix(installer): hydralink-Phase tatsächlich in install.sh + update.sh
5d88ac2 feat(installer): hydralink als Phase 11 ins HydraHive2-Setup (#83-#19)
33030a7 feat(agentlink): Dashboard-Link in System-Card + dev-start ENV
db02b1c feat(agentlink): WebSocket-Client für AgentLink — ask_agent live (#83)
281f793 fix(ui): 100vh → 100dvh — iOS-Layout rastet ein (#80)
131a893 feat(ui): Domain-Farben überall (#77 Phase 2)
b4c3c61 feat(ui): Bento-Menü farbig (#77 Phase 1)
36e972e feat(compaction): Variante B — Chunking für riesen Sessions (#81)
d0aafe4 fix(runner): temperature-Retry bei Anthropic 'deprecated'
2552a69 fix(agents): Pydantic-Models um compact_*-Felder erweitert (#82-Followup)
da54762 fix(agents): Compact-Settings-Save tolerant gegen None/leere Werte
28f7a6d feat(agents): Per-Agent Compaction-Settings (#82)
1e8d355 feat(chat): Bubble-Polish (#39)
9f90a61 fix(runner): Thinking-Blocks aus History strippen — \"Invalid signature\" (#79)
421c1a6 fix(chat): Vorlesen-Button — Hook-Order + Voices-Race (#76)
59c6035 fix(agents): ask_agent in Tool-Liste tolerieren wenn AgentLink fehlt (#78)
b6f3f55 docs(spec): Backup/Restore-Sektion ergänzt
cdcb8f5 feat(backup): System-Backup für Admin (B1.a)
+ Compliance-Refactor (98298d3, 0557044, 3da2ff6, 3fef573)
+ hydralink-Repo (d72da97, d9c8695)
```

## Live-Server (218)

- **Host**: 192.168.178.218, SSH-Alias `hh2-218`
- **Setup-User**: chucky (Passwort lummerland123, sudo-fähig)
- **Service-User**: hydrahive (no-login)
- **Repo**: /opt/hydrahive2 auf main (Stand 4755135)
- **Daten**: /var/lib/hydrahive2/
- **Config**: /etc/hydrahive2/
- **Frontend-URL**: https://192.168.178.218/
- **Admin-Passwort** auf 218: lummerland123
- **HydraLink-Stack** (jetzt auch live):
  - postgresql.service (apt) ✓
  - redis-server.service (apt, 127.0.0.1:6379) ✓
  - agentlink.service (systemd venv, 127.0.0.1:9000) ✓
  - agentlink-frontend.service (systemd python http.server, 127.0.0.1:9001) ✓
  - HydraHive verbindet via /etc/systemd/system/hydrahive2.service.d/agentlink.conf

## Lokales Dev-Setup (auf Tills Workstation)

- Repo: /home/till/claudeneu/ (HydraHive2)
- Repo: /home/till/hydralink/ (HydraLink)
- Dev-Service: hydrahive2-dev.service (user-systemd)
- Dev-URLs: Backend 8001, Frontend 5173, AgentLink 9000, AgentLink-Dashboard 9001
- dev-start.sh setzt HH_AGENTLINK_URL automatisch auf 127.0.0.1:9000

## AgentLink — Architektur

```
HydraHive Master Agent
       │
       │ ask_agent({agent_id:'specialist', task:'...'})
       ▼
hydrahive/agentlink/client.post_state(...)  ──► POST http://127.0.0.1:9000/states
       │                                            │
       │ register_pending(state.id) → Future        │
       │                                            ▼
       │                                    Postgres + Redis Pub/Sub
       │                                            │
       │                                            ▼
       │                              Specialist-Agent empfängt via WS
       │                                            │
       │ on_event handler im HydraHive-Lifespan ◄───┤
       │ resolve_pending(reply_to)                  │
       ▼
ask_agent return ToolResult mit Antwort-Inhalt
```

WS-Channel-Pattern: HydraHive subscribed `agent:hydrahive` (oder agent_id-Override).
Antwort-State referenziert Original via `handoff.reason = "reply_to:<state-id>"`.

## Was offen ist

### P1-Issues (groß, halber bis ganzer Build-Tag)

- **#38 User-Backup Self-Service** (DSGVO Art. 20) — komplementär zu System-Backup
- **#43 Edit + Resend** im Chat — User-Bubble klicken, ändern, Verlauf ab dort regenerieren
- **#55 ToolsSelector-Akkordeon** — Single-Expand pro Quelle (Core/Plugin/MCP)
- **#56 AgentForm Tabs + Sticky Save-Bar**
- **#57-#62 Projekt-Sektionen** — Tab-Layout + Statistiken + Sessions-Tab + Git-Status + Server-Tab
- **#26 Skills-System** — SPEC verspricht Markdown-Skills

### P2-Issues (häufig genutzt)

- **#40 Stop-Reason-Pill** im Chat
- **#42 Estimierte Kosten pro Bubble** (€/$)
- **#45 Copy-Button** + **#46 Retry-Button** im Chat
- **#50 Tool-Calls collapse-by-default**
- **#53 Drag-Drop Bilder** in Chat
- **#35 Discord-Channel-Adapter**
- **#63 Specialists-Tab** (jetzt mit AgentLink wirklich nutzbar!)
- **#67 Lifecycle (active/paused/archived)** für Projekte
- **#66 Notes/Briefing** pro Projekt

### P3 (~30 Issues, nice-to-have)

Tags, Audit, Member-Rechte, Webhooks, MCP/Plugin/LLM-Override pro Projekt,
Branching, Suche, Read-Receipts, Streaming-Animation, Pre-Compaction-Hint,
ZH-Locale, etc.

### Doku-Issues offen

- #15 ZH-Locale (SPEC sagt DE/EN/ZH, Code DE/EN)
- #22 CSP unsafe-inline (16 Inline-Styles)
- #32 PostgreSQL-Zeile in SPEC

## Empfohlener nächster Build-Tag

1. **Frauchen / echter User testet AgentLink** — die Specialists-Disclosure
   und Master→Specialist-Handoff am echten Use-Case durchspielen
2. **#43 Edit + Resend** — kleines aber sehr sichtbares UX-Feature
3. **#56 AgentForm Tabs** — die Compaction-Section wandert in einen
   `Erweitert`-Tab, sticky save-bar
4. **#57-#62 Projekt-Sektionen Phase 1** — Tabs + Sessions + Statistiken

## Nicht-vergessen-Liste

- AgentLink-Dashboard auf 218: https://hh2-218 → System-Page → \"Dashboard öffnen\"
  öffnet http://192.168.178.218:9001 — falls Browser CORS warnt: ist
  Mixed-Content (HTTPS-Page → HTTP-Frontend), evtl. nginx-Reverse-Proxy
  für AgentLink-Frontend wenn HTTPS überall werden soll.
- 218 IP-Wechsel-Problem (DHCP-Lease) bleibt — DHCP-Reservation auf
  Fritzbox wäre stabiler.
- Self-Update-Falle: bash hält update.sh-Inhalt im Speicher beim Start.
  Nach git pull läuft Rest mit altem Code. Bei größeren Änderungen
  zweites Mal aufrufen.
