# HydraHive2 — Verzeichnisstruktur

## Übersicht

```
hydrahive2.0/
├── SPEC.md                    ← Produktspezifikation (heilig)
├── CLAUDE.md                  ← Arbeitsregeln für KI-Sessions
├── docs/                      ← Dokumentation
├── core/                      ← Python Backend (FastAPI)
│   └── src/hydrahive/
│       ├── settings/          ← Settings-Singleton (alle Pfade/Config)
│       ├── agents/
│       │   ├── master/        ← Masteragent-Logik
│       │   ├── project/       ← Projektagent-Logik
│       │   └── specialist/    ← Spezialist-Logik
│       ├── tools/             ← Je Tool eine Datei (shell.py, file_read.py, ...)
│       ├── llm/               ← LLM-Client, Streaming, Failover
│       ├── api/
│       │   ├── routes/        ← Je Ressource eine Datei (agents.py, projects.py, ...)
│       │   └── middleware/    ← Auth, Rate-Limiting, Logging
│       ├── agentlink/         ← AgentLink-Client (nur Client, kein Server-Code)
│       ├── messaging/         ← WhatsApp, Discord, Telegram, Matrix
│       └── plugins/           ← Plugin-Loader
├── console/                   ← React/TypeScript Frontend
│   └── src/
│       ├── features/          ← Feature-Folders (co-located)
│       │   ├── auth/          ← Login, Permissions (EINZIGE Permissions-Quelle)
│       │   ├── chat/          ← Chat UI + Hook + API + Types
│       │   ├── agents/        ← Agents UI + Hook + API + Types
│       │   ├── projects/      ← Projekte UI + Hook + API + Types
│       │   ├── specialists/   ← Spezialisten UI + Hook + API + Types
│       │   ├── llm/           ← LLM-Config UI
│       │   ├── mcp/           ← MCP-Server UI
│       │   ├── system/        ← System/Logs UI
│       │   └── backup/        ← Backup/Restore UI
│       ├── components/
│       │   ├── ui/            ← Basiskomponenten (Button, Input, Modal, ...)
│       │   └── layout/        ← Shell, Sidebar, BottomNav
│       ├── lib/               ← api.ts, sseStream.ts (generische Utils)
│       └── i18n/              ← DE, EN, ZH Übersetzungen
└── installer/
    ├── install.sh             ← Haupt-Installer
    ├── update.sh              ← Update-Skript
    ├── modules/               ← Installer-Module (01_os.sh, 02_deps.sh, ...)
    └── templates/             ← Agent-Templates
```

## Regeln

- **Max ~150 Zeilen pro Datei** — Eine Datei, eine Verantwortung
- **Co-location** — Alles was zusammengehört liegt zusammen (Feature-Folder)
- **Permissions** — Nur in `features/auth/permissions.ts` (Frontend) bzw. `api/middleware/auth.py` (Backend)
- **Config** — Nur über Settings-Singleton, nie hardcoded
