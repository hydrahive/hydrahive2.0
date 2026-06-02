# HydraHive2 — Feature-Landkarte

> **Was/Wie/Wo/Warum** des ganzen Systems. Damit niemand mehr (Mensch oder Agent)
> zufällig entdeckt, was längst funktioniert.
>
> Erstellt 2026-06-02 in der „Feldforschung" — zwei parallele Läufe an derselben
> Aufgabe, beide auf Anthropic-Modellen:
> - **Referenz-Schicht** (dieser Ordner, `NN-*.md`): Fan-out mit **Opus 4.8**, ein Agent pro
>   Subsystem, exhaustiv mit `datei:zeile`. 26 Sektionen, ~11.800 Zeilen.
> - **Überblick-Schicht** (`uebersicht/`): **Sonnet 4.6** als Einzelagent, 36 kompakte,
>   querverlinkte Architektur-Sektionen mit Tabellen & Flow-Diagrammen.

## So nutzt du sie

| Frage | Schicht |
|------|---------|
| „Versteh das System in 10 Minuten" | → **`uebersicht/00-overview.md`** + die Überblick-Sektionen |
| „Wo genau ist X, und welche Falle lauert?" | → die **Referenz-Sektionen** hier (`NN-*.md`) |

Die zwei Schichten sind absichtlich komplementär: Überblick = Onboarding, Referenz =
Nachschlagewerk. Bei Abweichungen gewinnt die Referenz-Schicht (frischer + `datei:zeile`).

---

## Referenz-Sektionen (Opus-4.8-Fan-out)

| # | Subsystem | Datei | Inhalt |
|---|-----------|-------|--------|
| 01 | Runner & Agent-Loop | [01-runner.md](01-runner.md) | Tool-Loop, System-Prompt-Komposition, LLM-Bridge (Stream/Fallback), Compaction-Trigger, Modell-Failover, Loop-Detection, Proaktiver Recall, Emote-Hint |
| 02 | Buddy | [02-buddy.md](02-buddy.md) | Lifetime-Session, Charaktere/Tone/Sprache, Slash-Commands, Soul, Left-/Right-Panel, `is_buddy`-Marker |
| 03 | Butler (Automation) | [03-butler.md](03-butler.md) | Registry (Triggers/Conditions/Actions), Dispatch, Executor, Templates, dry_run |
| 04 | Communication | [04-communication.md](04-communication.md) | Mail/IMAP/SMTP, WhatsApp/Baileys, Discord, Matrix, Agent-Glue, Sender-Rahmung, Voice |
| 05 | AgentLink | [05-agentlink.md](05-agentlink.md) | Inter-Agent-Transport (HTTP/WS), Handoff, Reconnect, `hh_al_*`-Tools, Spoofing-Schutz |
| 06 | Patientenakte & Health | [06-akte.md](06-akte.md) | Schema-SSOT, Entitäten, FHIR, EGA-Records, Apple-Health-Ingest, Zahnfee-Briefing |
| 07 | Datamining (Langzeitgedächtnis) | [07-datamining.md](07-datamining.md) | Live-Ingest externer Instanzen, Index, Volltextsuche, Stats, Transfer, Rechunk |
| 08 | LLM & Modelle | [08-llm.md](08-llm.md) | Provider, Live-Modell-Liste, media_models, Pricing, Reasoning-Effort, Embed, OAuth |
| 09 | MCP | [09-mcp.md](09-mcp.md) | Server-Registry, Tool-Bridge, Schema-Auflösung, hydrahive-eigener MCP-Server (`hh_*`) |
| 10 | Agent-Tools | [10-tools.md](10-tools.md) | Jedes Tool einzeln: shell, file_*, generate_image/video/music/speech, web_*, memory, ask_agent … |
| 11 | Voice (TTS/STT) | [11-voice.md](11-voice.md) | STT (incus 10300), 4 TTS-Provider, Vorlese-TTS, Voice-Input, WhatsApp-Voice |
| 12 | Plugins & Extensions | [12-plugins.md](12-plugins.md) | Plugin-System (Core nie für Plugins), Tool-Bridge, Docker-Extensions, Stream/Runner |
| 13 | Skills | [13-skills.md](13-skills.md) | Loader, Models, system_defaults, Skill-Aktivierung pro Agent |
| 14 | Projects | [14-projects.md](14-projects.md) | Projekt-Workspace, Git (manage/ops/info), Files, Samba, Servers, GH-Token-Injection |
| 15 | VMs | [15-vms.md](15-vms.md) | Lifecycle, ISOs, Imports, Snapshots, VNC, Ops |
| 16 | Containers | [16-containers.md](16-containers.md) | CRUD, Ops, Console (PTY/WS), Detail-View |
| 17 | Auth, Permissions & Users | [17-auth.md](17-auth.md) | Permissions-SSOT, JWT, Rollen, Rate-Limiting, Credential-Vault, Redaction, Login |
| 18 | DB & Persistence | [18-db.md](18-db.md) | SQLite-Schema, alle Migrationen (NNN_-Prefix), Tabellen, db()-Context, Settings-Singleton |
| 19 | Memory & Cards (Recall) | [19-memory.md](19-memory.md) | Memory-Store, Crystallize, Cards (recency×salience), Proaktiver Recall A/C, Embed/Suche |
| 20 | Federation & Streaming | [20-federation.md](20-federation.md) | Federation (TLS-Verify), Streaming-Page, externe Instanzen, SSE |
| 21 | Infra (Backup/Tailscale/Samba/Net) | [21-infra.md](21-infra.md) | Backup/Restore (Manifest/Tar/Versionierung), Tailscale, Samba-Shares, Netzwerk |
| 22 | System, Dashboard & Admin | [22-system.md](22-system.md) | Dashboard-Summary, Health-Strip, Token-Audit, Update/Rebuild, Admin, Analytics |
| 23 | Scratchpad | [23-scratchpad.md](23-scratchpad.md) | Globaler Scratchpad (2 Zonen user/agent), Markdown, Tool + Hinweis-Mechanik |
| 24 | Research | [24-research.md](24-research.md) | Research-APIs, externe Recherche-Integration |
| 25 | Frontend-Shell, Chat & Workspace | [25-frontend.md](25-frontend.md) | Routing, Layout/Topbar, Chat-Thread/Bubbles/Emotes, Workspace (Monaco/Git), Redesign, i18n |
| 26 | **Querschnitt: End-to-End & Glue** | [26-glue.md](26-glue.md) | Eine Nachricht Klick→API→Runner→LLM→Tools→DB→SSE→UI. Session-Lifecycle. Die load-bearing Verdrahtung. |

## Überblick-Schicht (Sonnet-4.6-Einzelagent)

36 kompakte Sektionen unter [`uebersicht/`](uebersicht/) — Start: [`uebersicht/00-overview.md`](uebersicht/00-overview.md).
Feinere Aufteilung (trennt u.a. webmin, system-hooks, multimodal, zahnfee, samba einzeln), Tabellen + ASCII-Flows.

---

## Methodik / Erkenntnis

Gleicher Provider, also isoliert der Doppellauf **Architektur** statt Modell-Marke:
**Fan-out** (ein fokussierter Agent pro Subsystem) liefert mehr Tiefe & `datei:zeile`;
ein **Einzelagent** über alles liefert besseren Überblick & Querverlinkung, aber muss die
Aufmerksamkeit strecken. Beides taugt — für verschiedene Zwecke.

Generierungs-Aufwand Referenz-Schicht: ~4,3 Mio Tokens, 24 Agenten, ~44 Min (in 5er-Wellen
gegen das Anthropic-Rate-Limit gedrosselt). Ein Burst von 14 parallel hatte vorher das
Org-Limit getriggert — Lehre: große Fan-outs in Wellen fahren.
