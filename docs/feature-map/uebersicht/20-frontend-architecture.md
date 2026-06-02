# Feature Map: Frontend-Architektur

> **Pfad:** `frontend/src/`  
> **Stack:** React 18, TypeScript, Vite, Tailwind CSS, React Router  
> **Was:** Struktur, Routing, State-Management, Shared-Components des Frontends.

---

## Verzeichnis-Struktur

```
frontend/src/
├── features/              # Feature-basierte Co-location (HAUPT-PATTERN)
│   ├── agents/            # Agent-Verwaltung
│   ├── analytics/         # Session-Analytics
│   ├── auth/              # Login, JWT, Permissions
│   ├── buddy/             # Buddy-Chat + Settings
│   ├── butler/            # Butler Flow-Builder
│   ├── chat/              # Haupt-Chat UI
│   ├── communication/     # Messenger-Config (WhatsApp, Discord)
│   ├── containers/        # Container-Management
│   ├── credentials/       # Credential-Store UI
│   ├── dashboard/         # Dashboard
│   ├── datamining/        # Datamining/Analytics UI
│   ├── extensions/        # Extensions-UI
│   ├── federation/        # Federation-UI
│   ├── health/            # Gesundheitsakte + Apple Health
│   ├── help/              # Hilfe-Seiten
│   ├── llm/               # LLM-Provider-Config + Media-Models
│   ├── mcp/               # MCP-Server-Config
│   ├── memory/            # Memory-Viewer
│   ├── plugins/           # Plugin-Hub UI
│   ├── profile/           # User-Profil
│   ├── projects/          # Projekt-Verwaltung
│   ├── scratchpad/        # Scratchpad UI
│   ├── skills/            # Skills-Verwaltung
│   ├── streaming/         # Streaming-Config
│   ├── system/            # System-Admin
│   ├── users/             # User-Verwaltung
│   ├── vms/               # VM-Verwaltung
│   └── zahnfee/           # Zahnfee-UI
├── shared/                # Geteilte Komponenten + Utilities
│   ├── components/        # Button, Modal, Input, ...
│   ├── hooks/             # useApi, useDebounce, ...
│   └── utils/             # Formatierung, Datum, ...
├── assets/                # Statische Assets (Fonts, globale Icons)
├── i18n/                  # Internationalisierung
│   ├── locales/           # de.json, en.json
│   └── help/              # Hilfe-Texte pro Sprache
└── main.tsx               # App-Entry-Point
```

---

## Feature-Folder-Pattern

**Alles was zusammengehört liegt zusammen:**

```
features/chat/
├── ChatPage.tsx      ← Seite
├── useChat.ts        ← State-Hook
├── api.ts            ← API-Calls
├── types.ts          ← TypeScript-Typen
├── MessageInput.tsx  ← Komponente
├── ...
└── workspace/        ← Sub-Feature
    ├── WorkspacePanel.tsx
    └── ...
```

**Verboten:** Business-Logic in shared/. Shared enthält nur generische UI-Primitives.

---

## Routing (React Router)

Alle Routen in `main.tsx` oder einem zentralen `routes.ts`:

| Route | Feature | Beschreibung |
|---|---|---|
| `/` | dashboard | Dashboard |
| `/buddy` | buddy | Buddy-Chat |
| `/chat` | chat | Agent-Chat |
| `/projects` | projects | Projekt-Liste |
| `/agents` | agents | Agent-Verwaltung |
| `/butler` | butler | Flow-Builder |
| `/datamining` | datamining | Analytics |
| `/health` | health | Gesundheitsakte |
| `/communication` | communication | Messenger-Config |
| `/plugins` | plugins | Plugin-Hub |
| `/skills` | skills | Skills-Verwaltung |
| `/llm` | llm | LLM-Config |
| `/mcp` | mcp | MCP-Server |
| `/credentials` | credentials | Credentials |
| `/vms` | vms | VM-Verwaltung |
| `/containers` | containers | Container |
| `/extensions` | extensions | Extensions |
| `/federation` | federation | Federation |
| `/backup` | system | Backup |
| `/users` | users | User-Admin |
| `/profile` | profile | Profil |
| `/scratchpad` | scratchpad | Scratchpad |
| `/login` | auth | Login |

---

## State-Management

**Kein globaler Redux-Store.** Stattdessen:

1. **React Query / SWR** für Server-State (API-Daten, Caching)
2. **Zustand** für globalen Client-State (Auth, Theme, ...)
3. **Local useState** für Komponenten-State
4. **Custom Hooks** (`useChat`, `useBuddy`, ...) für Feature-State

```typescript
// Auth-State (useAuthStore.ts — Zustand)
const { user, token, login, logout } = useAuthStore()

// Chat-State (useChat.ts — local + React Query)
const { messages, send, isStreaming } = useChat(sessionId)
```

---

## API-Calls Pattern

Jedes Feature hat eine `api.ts`:

```typescript
// features/chat/api.ts
export const chatApi = {
  getSessions: () => api.get<Session[]>('/chat/sessions'),
  createSession: (data: CreateSessionDto) => api.post<Session>('/chat/sessions', data),
  sendMessage: (sessionId: string, content: string) => 
    api.post(`/chat/sessions/${sessionId}/messages`, { content }),
}
```

---

## Permissions

**Einzige Quelle:** `features/auth/permissions.ts`

```typescript
export const PERMISSIONS = {
  ADMIN: 'admin',
  MANAGE_USERS: 'manage_users',
  VIEW_DATAMINING: 'view_datamining',
  ...
} as const

// Verwendung:
const canAdmin = usePermission(PERMISSIONS.ADMIN)
```

---

## TypeScript-Checks (CRITICAL)

```bash
# RICHTIG (prüft wirklich):
cd frontend && ./node_modules/.bin/tsc -b

# FALSCH (prüft NIE — root tsconfig hat files:[]):
cd frontend && tsc --noEmit
```

Grund: `tsconfig.json` im Root hat `files: []` und nur `references` — 
`--noEmit` ohne `-b` typecheckt deshalb gar nichts.

---

## Build

```bash
cd frontend
npm install
npm run build        # → dist/ (statische Dateien)
npm run dev          # → Dev-Server Port 5173
./node_modules/.bin/tsc -b  # Typecheck
```

Vite-Build landet in `frontend/dist/` → nginx serviert das.

---

## Verwandte Subsysteme

- **→ Chat UI** (`19-frontend-chat.md`): größtes Feature
- **→ Buddy** (`09-buddy.md`): eigene Feature-Section
- **→ Auth/Security** (`21-auth-security.md`): JWT-Handling im Frontend
