# HydraHive2 — Verzeichnisstruktur

> **Last Updated:** 2026-05-09 — Snapshot, kein Designdokument.
> Quelle der Wahrheit ist der Code, nicht diese Datei.
> Backend: 343 .py-Files, 243 Tests in 17 Test-Dateien.
> Frontend: 262 .ts/.tsx-Files, 23 Feature-Folders.

## Übersicht

```
hydrahive2.0/
├── SPEC.md                    ← Produktspezifikation (heilig)
├── CLAUDE.md                  ← Arbeitsregeln für KI-Sessions
├── README.md
├── CONTRIBUTING.md
├── dev-start.sh               ← Backend + Frontend lokal starten
├── docs/                      ← HANDOVER, STRUCTURE, TESTING_STATUS, …
├── core/                      ← Python Backend (FastAPI)
│   ├── pyproject.toml
│   ├── tests/                 ← 17 Dateien, 243 Tests (siehe TESTING_STATUS.md)
│   └── src/hydrahive/
│       ├── api/               ← FastAPI-Entry + Routen + Middleware
│       │   ├── main.py
│       │   ├── routes/        ← Je Ressource ≥1 Datei (agents.py, butler.py, …)
│       │   └── middleware/    ← Auth, Rate-Limiting, Logging
│       ├── settings/          ← Settings-Singleton
│       ├── auth/              ← JWT, Login-Lockout, Permissions
│       ├── agents/            ← Defaults, Config-Utils (master/ + project/ leere Stubs)
│       ├── runner/            ← Tool-Loop, Dispatcher, Codex/LiteLLM-Bridge
│       ├── compaction/        ← Append-only Compaction (firstKeptEntryId)
│       ├── llm/               ← LiteLLM-Wrapper, Provider-Catalog, Streaming
│       ├── tools/             ← Built-in Tools (shell, file_*, fetch_url, datamining, …)
│       ├── mcp/               ← MCP-Client (stdio + HTTP-Streamable + SSE)
│       ├── plugins/           ← Plugin-Loader
│       ├── skills/            ← SKILL.md-Loader + system_defaults/
│       ├── projects/
│       ├── db/                ← SQLite-Connection, Messages, Sessions
│       ├── credentials/       ← Provider-Credentials (LLM, OAuth)
│       ├── oauth/             ← Anthropic / OpenAI Codex / MiniMax Flows
│       ├── backup/            ← Backup/Restore
│       ├── communication/     ← Discord, WhatsApp (Baileys-Bridge subprocess)
│       ├── messaging/
│       ├── voice/             ← Voice-Subsystem
│       ├── containers/        ← incus/LXC-Management
│       ├── vms/               ← QEMU/KVM-Management
│       ├── samba/             ← Samba-Share-Verwaltung
│       ├── tailscale/         ← Tailscale-Integration
│       ├── agentlink/         ← AgentLink-Client (kein Server-Code im Core)
│       ├── buddy/             ← (SPEC: Tier 0)
│       ├── butler/            ← ReactFlow-Flow-Engine Backend
│       └── zahnfee/           ← (SPEC: Stub)
├── frontend/                  ← React 19 + TypeScript + Vite
│   └── src/
│       ├── features/          ← Feature-Folders (co-located)
│       │   ├── auth/          ← Login + Permissions (einzige Quelle)
│       │   ├── chat/          ← Chat UI + Tool-Cards
│       │   ├── agents/
│       │   ├── projects/
│       │   ├── llm/
│       │   ├── mcp/
│       │   ├── memory/
│       │   ├── datamining/
│       │   ├── butler/
│       │   ├── extensions/
│       │   ├── plugins/
│       │   ├── containers/, vms/, communication/, voice/-Stub …
│       │   ├── skills/, profile/, dashboard/, system/, users/, help/
│       │   ├── buddy/, zahnfee/
│       ├── components/        ← Basis-UI + Layout
│       ├── lib/               ← api.ts, sseStream.ts
│       └── i18n/              ← DE/EN/ZH (+ help/)
├── installer/
│   ├── install.sh             ← Idempotent, --no-prompt, --reconfigure
│   ├── update.sh              ← Self-Heal-Re-Exec
│   ├── modules/               ← 9 optionale Komponenten (Tailscale, Postgres, …)
│   └── git-hooks/             ← pre-commit (SPEC.md/CLAUDE.md standalone)
├── extensions/                ← Self-Hosted-Apps (Vaultwarden, SearXNG, Pi-hole, …)
└── mcp-servers/               ← Mitgelieferte MCP-Server
```

## Regeln

- **Max ~200 Zeilen pro Datei** — eine Datei, eine Verantwortung
- **Co-location** — alles was zusammengehört liegt zusammen (Feature-Folder im Frontend, Modul-Folder im Backend)
- **Permissions** — Frontend: `features/auth/`, Backend: `auth/` + `api/middleware/auth.py`
- **Config** — nur über Settings-Singleton, nie hardcoded
- **SPEC.md / CLAUDE.md** — standalone-Commits (Pre-Commit-Hook erzwingt)
