# Chat Workspace Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Den normalen Chat (`ChatPage`) auf ein Drei-Panel-Layout umbauen — Sessions+Modell/Tiefe links, Chat mitte, Workspace-Browser mit Monaco-Editor und Git-Integration rechts. Buddy bleibt unverändert.

**Architecture:** Neue Feature-Unterordner `chat/layout/` und `chat/workspace/`. `ChatPage` orchestriert nur. Neue Backend-Route `/api/workspace` mit hart validierter Pfad-Wurzel (`workspace_for(agent)`, kein Override). Editor (Monaco) und Git-Status lazy geladen.

**Tech Stack:** React 18 + TypeScript + Vite, Monaco Editor (dynamic import), FastAPI + pytest, GitPython/subprocess (bestehende `_git_ops`).

**Spec:** `docs/superpowers/specs/2026-06-02-chat-workspace-redesign-design.md`
**Rollback-Tag:** `pre-chat-workspace-redesign`

---

## Datei-Struktur

| Datei | Aktion | Verantwortung |
|---|---|---|
| `frontend/src/features/chat/layout/ThreePanelLayout.tsx` | CREATE | 3-Spalten-Grid + Kollaps-States (localStorage) |
| `frontend/src/features/chat/layout/CollapsiblePanel.tsx` | CREATE | Wiederverwendbarer Panel-Wrapper links/rechts |
| `frontend/src/features/chat/workspace/api.ts` | CREATE | Workspace/Git-API-Client |
| `frontend/src/features/chat/workspace/useWorkspace.ts` | CREATE | State: Pfad, offene Datei, Git-Status |
| `frontend/src/features/chat/workspace/WorkspacePanel.tsx` | CREATE | Dach: Tabs + Pfad-Anzeige |
| `frontend/src/features/chat/workspace/FileTree.tsx` | CREATE | Lazy Dateibaum mit Git-Markern |
| `frontend/src/features/chat/workspace/FileEditor.tsx` | CREATE | Monaco-Editor (dynamic import) |
| `frontend/src/features/chat/workspace/GitPanel.tsx` | CREATE | Status + Diff + Stage + Commit |
| `frontend/src/features/chat/ChatPage.tsx` | MODIFY | Auf ThreePanelLayout umstellen |
| `frontend/src/features/chat/SessionList.tsx` | MODIFY | Footer: Modell + Tiefe |
| `frontend/src/features/chat/_ChatHeader.tsx` | MODIFY | Modell/Effort raus, Token-Ring rein |
| `frontend/src/i18n/locales/{de,en}/workspace.json` | CREATE | i18n-Namespace |
| `core/src/hydrahive/api/routes/workspace.py` | CREATE | File + Git Endpunkte |
| `core/src/hydrahive/workspace/_paths.py` | CREATE | Pfad-Validierung (Traversal-Schutz) |
| `core/src/hydrahive/workspace/_tree.py` | CREATE | Verzeichnis-Listing |
| `core/src/hydrahive/workspace/_git_status.py` | CREATE | Git status/diff/stage/commit (workspace-scoped) |
| `core/tests/test_workspace_api.py` | CREATE | API-Tests |
| `core/tests/test_workspace_paths.py` | CREATE | Pfad-Validierungs-Tests |

---

## Phase 1 — Layout-Gerüst

Ziel: 3-Spalten-Layout steht, Kollaps funktioniert, Modell+Tiefe links unten, Chat läuft unverändert. Workspace-Panel ist Platzhalter.

### Task 1: CollapsiblePanel-Komponente

**Files:**
- Create: `frontend/src/features/chat/layout/CollapsiblePanel.tsx`

- [ ] **Step 1: Datei anlegen**

```tsx
import { ChevronLeft, ChevronRight } from "lucide-react"

interface Props {
  side: "left" | "right"
  open: boolean
  onToggle: () => void
  width: number
  children: React.ReactNode
}

export function CollapsiblePanel({ side, open, onToggle, width, children }: Props) {
  const ChevOpen = side === "left" ? ChevronLeft : ChevronRight
  const ChevClosed = side === "left" ? ChevronRight : ChevronLeft
  const borderSide = side === "left" ? "border-r" : "border-l"

  if (!open) {
    return (
      <div className={`w-8 flex-shrink-0 ${borderSide} border-white/[8%] bg-white/[1%] flex items-start justify-center pt-3`}>
        <button onClick={onToggle} className="p-1 rounded text-zinc-500 hover:text-violet-300 hover:bg-white/5 transition-colors">
          <ChevClosed size={14} />
        </button>
      </div>
    )
  }

  return (
    <aside className={`flex-shrink-0 ${borderSide} border-white/[8%] bg-white/[1%] flex flex-col`} style={{ width }}>
      <div className="flex-1 min-h-0 flex flex-col">{children}</div>
      <button onClick={onToggle} className={`flex items-center justify-center py-1.5 border-t border-white/[6%] text-zinc-600 hover:text-violet-300 hover:bg-white/5 transition-colors`}>
        <ChevOpen size={13} />
      </button>
    </aside>
  )
}
```

- [ ] **Step 2: Build prüfen**

Run: `cd frontend && npm run build 2>&1 | grep -E "error TS|✓ built"`
Expected: `✓ built`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/chat/layout/CollapsiblePanel.tsx
git commit -m "feat(chat): CollapsiblePanel-Wrapper für 3-Panel-Layout"
```

### Task 2: ThreePanelLayout-Komponente

**Files:**
- Create: `frontend/src/features/chat/layout/ThreePanelLayout.tsx`

- [ ] **Step 1: Datei anlegen**

```tsx
import { useState, useEffect } from "react"
import { CollapsiblePanel } from "./CollapsiblePanel"

interface PanelState { left: boolean; right: boolean }
const STORAGE_KEY = "hh2.chat.panels"

function loadState(): PanelState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return { left: true, right: true }
}

interface Props {
  left: React.ReactNode
  center: React.ReactNode
  right: React.ReactNode
}

export function ThreePanelLayout({ left, center, right }: Props) {
  const [panels, setPanels] = useState<PanelState>(loadState)

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(panels)) } catch { /* ignore */ }
  }, [panels])

  return (
    <div className="flex h-[calc(100dvh-3rem)] -m-4 md:-m-6">
      <CollapsiblePanel side="left" open={panels.left} width={230}
        onToggle={() => setPanels((p) => ({ ...p, left: !p.left }))}>
        {left}
      </CollapsiblePanel>
      <main className="flex-1 flex flex-col min-w-0">{center}</main>
      <CollapsiblePanel side="right" open={panels.right} width={300}
        onToggle={() => setPanels((p) => ({ ...p, right: !p.right }))}>
        {right}
      </CollapsiblePanel>
    </div>
  )
}
```

- [ ] **Step 2: Build prüfen**

Run: `cd frontend && npm run build 2>&1 | grep -E "error TS|✓ built"`
Expected: `✓ built`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/chat/layout/ThreePanelLayout.tsx
git commit -m "feat(chat): ThreePanelLayout mit localStorage-Kollaps-Persistenz"
```

### Task 3: Modell + Tiefe in SessionList-Footer

**Files:**
- Modify: `frontend/src/features/chat/SessionList.tsx`

Kontext: Aktuell wird `ModelPicker` + `ReasoningEffortPill` im `_ChatHeader.tsx` gerendert. Sie wandern in den Footer der SessionList. SessionList bekommt dazu die nötigen Props (aktiver Agent, Callbacks).

- [ ] **Step 1: Aktuelle SessionList lesen**

Run: `cat frontend/src/features/chat/SessionList.tsx`
Verstehen: Welche Props kommen rein, wie ist der Footer-Bereich (Agent-Selector) aufgebaut.

- [ ] **Step 2: Props erweitern + Footer rendern**

In den `Props`-Interface von SessionList ergänzen:
```tsx
  activeAgent?: { id: string; llm_model?: string; reasoning_effort?: string | null } | null
  onModelChange?: (model: string | null) => void
  onEffortChange?: (effort: string | null) => Promise<void>
  effortExtended?: boolean
```

Im Footer (nach dem Agent-Selector), Imports oben ergänzen:
```tsx
import { ModelPicker } from "./ModelPicker"
import { ReasoningEffortPill } from "./ReasoningEffortPill"
import { useTranslation } from "react-i18next"
```

Footer-Block (vor dem schließenden Container):
```tsx
{activeAgent && (
  <div className="border-t border-white/[8%] bg-black/20">
    <div className="px-2.5 py-2 border-b border-white/[5%] flex items-center gap-2">
      <span className="text-[9px] uppercase tracking-wider text-zinc-600 w-9 shrink-0">{t("model")}</span>
      <div className="flex-1 min-w-0">
        <ModelPicker current={activeAgent.llm_model ?? null}
          hint={t("model_hint")} onPick={(m) => onModelChange?.(m)} />
      </div>
    </div>
    <div className="px-2.5 py-2 flex items-center gap-2">
      <span className="text-[9px] uppercase tracking-wider text-zinc-600 w-9 shrink-0">{t("effort")}</span>
      <ReasoningEffortPill current={activeAgent.reasoning_effort}
        extended={effortExtended} onSelect={async (e) => { await onEffortChange?.(e) }} />
    </div>
  </div>
)}
```

Und `const { t } = useTranslation("chat")` am Anfang der Komponente.

- [ ] **Step 3: chat.json um `model` + `effort` ergänzen**

In `frontend/src/i18n/locales/de/chat.json` (model_hint existiert schon):
```json
  "effort": { "off_label": "Aus", "label": "Tiefe", ... }
```
Falls `effort.label` und `model` (Label) fehlen, ergänzen. de: `"model": "Modell"`, `"effort_label": "Tiefe"`. en analog: `"model": "Model"`, `"effort_label": "Depth"`.

(Hinweis: `effort.*`-Block existiert bereits aus i18n-Arbeit; nur Top-Level-Labels `model`/`effort` ergänzen falls nicht vorhanden. Im Footer `t("model")` → `t("effort_label")` verwenden statt `t("effort")` um Kollision mit dem bestehenden `effort`-Objekt zu vermeiden.)

- [ ] **Step 4: Build prüfen**

Run: `cd frontend && npm run build 2>&1 | grep -E "error TS|✓ built"`
Expected: `✓ built`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/chat/SessionList.tsx frontend/src/i18n/locales/de/chat.json frontend/src/i18n/locales/en/chat.json
git commit -m "feat(chat): Modell-Picker + Tiefe in SessionList-Footer"
```

### Task 4: ChatHeader aufräumen + ChatPage auf ThreePanelLayout

**Files:**
- Modify: `frontend/src/features/chat/_ChatHeader.tsx`
- Modify: `frontend/src/features/chat/ChatPage.tsx`

- [ ] **Step 1: ModelPicker + ReasoningEffortPill aus ChatHeader entfernen**

In `_ChatHeader.tsx` die `ModelPicker`- und `ReasoningEffortPill`-Nutzung im Header entfernen (sie sind jetzt in SessionList). Token-Ring/TokenMeter bleibt. Die zugehörigen Props (`onAgentChanged` für Modell) wandern mit.

- [ ] **Step 2: ChatPage umstellen**

In `ChatPage.tsx` den Return-Block (Zeile ~196-299) umbauen: Statt `<main>` + `<CollapsibleSidebar>` jetzt `<ThreePanelLayout>` mit drei Slots:
- `left`: `<SessionList … activeAgent={activeAgent} onModelChange={…} onEffortChange={…} />`
- `center`: der bestehende Chat-Block (ChatSearchProvider … MessageInput)
- `right`: vorerst `<div className="p-4 text-xs text-zinc-600">Workspace folgt…</div>`

Imports: `ThreePanelLayout` rein, `CollapsibleSidebar` raus. Modell/Effort-Handler die vorher im Header waren, hier definieren und an SessionList geben.

- [ ] **Step 3: Build prüfen**

Run: `cd frontend && npm run build 2>&1 | grep -E "error TS|✓ built"`
Expected: `✓ built`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/chat/_ChatHeader.tsx frontend/src/features/chat/ChatPage.tsx
git commit -m "feat(chat): ChatPage auf ThreePanelLayout, Header aufgeräumt"
```

- [ ] **Step 5: Till testet Phase 1**

Push + Deploy. Till prüft: 3 Spalten sichtbar, beide Panels kollabierbar (State bleibt nach Reload), Modell+Tiefe links unten funktionieren, Chat läuft wie vorher, Quick-Action-Pills da.

---

## Phase 2 — File-Browser (read-only)

Ziel: Backend liefert Dateibaum + Dateiinhalt (validiert), Frontend zeigt Tree + Vorschau.

### Task 5: Pfad-Validierung (Backend)

**Files:**
- Create: `core/src/hydrahive/workspace/__init__.py` (leer)
- Create: `core/src/hydrahive/workspace/_paths.py`
- Test: `core/tests/test_workspace_paths.py`

- [ ] **Step 1: Failing test schreiben**

```python
# core/tests/test_workspace_paths.py
from __future__ import annotations
import pytest
from pathlib import Path
from hydrahive.workspace._paths import resolve_in_workspace, WorkspacePathError


def test_resolves_relative_path(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "f.txt").write_text("x")
    result = resolve_in_workspace(tmp_path, "sub/f.txt")
    assert result == (tmp_path / "sub" / "f.txt").resolve()


def test_rejects_traversal(tmp_path: Path):
    with pytest.raises(WorkspacePathError):
        resolve_in_workspace(tmp_path, "../../etc/passwd")


def test_rejects_absolute_escape(tmp_path: Path):
    with pytest.raises(WorkspacePathError):
        resolve_in_workspace(tmp_path, "/etc/passwd")


def test_empty_path_returns_root(tmp_path: Path):
    assert resolve_in_workspace(tmp_path, "") == tmp_path.resolve()
```

- [ ] **Step 2: Test laufen lassen — muss fehlschlagen**

Run: `cd core && python -m pytest tests/test_workspace_paths.py -v`
Expected: FAIL (`ModuleNotFoundError: hydrahive.workspace._paths`)

- [ ] **Step 3: Implementierung**

```python
# core/src/hydrahive/workspace/_paths.py
from __future__ import annotations
from pathlib import Path


class WorkspacePathError(Exception):
    """Pfad liegt ausserhalb des erlaubten Workspace."""


def resolve_in_workspace(root: Path, rel: str) -> Path:
    """Löst `rel` relativ zu `root` auf und stellt sicher, dass das Ergebnis
    innerhalb von `root` bleibt. Schützt gegen `..`-Traversal, absolute Pfade
    und Symlink-Ausbrüche.
    """
    root_resolved = root.resolve()
    # Absolute Pfade nie akzeptieren — immer relativ interpretieren
    candidate = (root_resolved / rel.lstrip("/")).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise WorkspacePathError(f"Pfad ausserhalb des Workspace: {rel}")
    return candidate
```

- [ ] **Step 4: Test laufen lassen — muss passen**

Run: `cd core && python -m pytest tests/test_workspace_paths.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add core/src/hydrahive/workspace/ core/tests/test_workspace_paths.py
git commit -m "feat(workspace): Pfad-Validierung mit Traversal-Schutz"
```

### Task 6: Verzeichnis-Listing + Datei lesen (Backend)

**Files:**
- Create: `core/src/hydrahive/workspace/_tree.py`

- [ ] **Step 1: Implementierung**

```python
# core/src/hydrahive/workspace/_tree.py
from __future__ import annotations
from pathlib import Path

MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB


def list_dir(abs_path: Path) -> list[dict]:
    """Eine Ebene listen. Ordner zuerst, dann Dateien, alphabetisch."""
    if not abs_path.is_dir():
        raise NotADirectoryError(str(abs_path))
    entries = []
    for child in sorted(abs_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if child.name.startswith(".git"):
            continue
        entries.append({
            "name": child.name,
            "is_dir": child.is_dir(),
            "size": child.stat().st_size if child.is_file() else None,
        })
    return entries


def read_file(abs_path: Path) -> str:
    """Datei als Text lesen. Wirft bei zu groß oder Binär."""
    if not abs_path.is_file():
        raise FileNotFoundError(str(abs_path))
    if abs_path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("file_too_large")
    return abs_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Commit**

```bash
git add core/src/hydrahive/workspace/_tree.py
git commit -m "feat(workspace): Verzeichnis-Listing + Datei lesen"
```

### Task 7: Workspace-API-Route (tree + file GET)

**Files:**
- Create: `core/src/hydrahive/api/routes/workspace.py`
- Modify: `core/src/hydrahive/api/main.py` (Router registrieren)
- Test: `core/tests/test_workspace_api.py`

- [ ] **Step 1: Failing test schreiben**

```python
# core/tests/test_workspace_api.py
from __future__ import annotations
from tests.conftest import error_code


def _agent(client, admin_headers):
    res = client.post("/api/agents", headers=admin_headers,
                      json={"type": "specialist", "name": "WS Bot", "llm_model": "claude-haiku-4-5-20251001"})
    assert res.status_code == 201, res.text
    return res.json()


def test_tree_requires_auth(client):
    res = client.get("/api/workspace/tree?agent_id=x&path=")
    assert res.status_code == 401


def test_tree_lists_workspace(client, admin_headers):
    agent = _agent(client, admin_headers)
    res = client.get(f"/api/workspace/tree?agent_id={agent['id']}&path=", headers=admin_headers)
    assert res.status_code == 200, res.text
    assert isinstance(res.json(), list)


def test_tree_rejects_traversal(client, admin_headers):
    agent = _agent(client, admin_headers)
    res = client.get(f"/api/workspace/tree?agent_id={agent['id']}&path=../../etc", headers=admin_headers)
    assert res.status_code == 403
```

- [ ] **Step 2: Test laufen — muss fehlschlagen**

Run: `cd core && python -m pytest tests/test_workspace_api.py -v`
Expected: FAIL (404, Route existiert nicht)

- [ ] **Step 3: Route implementieren**

```python
# core/src/hydrahive/api/routes/workspace.py
from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query

from hydrahive.api.middleware.auth import require_auth
from hydrahive.agents import config as agents_config
from hydrahive.agents._paths import workspace_for, ensure_workspace
from hydrahive.workspace._paths import resolve_in_workspace, WorkspacePathError
from hydrahive.workspace._tree import list_dir, read_file

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


def _root_for(agent_id: str, user_id: str, role: str):
    agent = agents_config.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent_not_found")
    return ensure_workspace(agent)


@router.get("/tree")
def get_tree(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    agent_id: str = Query(...),
    path: str = Query(""),
) -> list[dict]:
    root = _root_for(agent_id, *auth)
    try:
        abs_path = resolve_in_workspace(root, path)
    except WorkspacePathError:
        raise HTTPException(status_code=403, detail="path_outside_workspace")
    try:
        return list_dir(abs_path)
    except NotADirectoryError:
        raise HTTPException(status_code=400, detail="not_a_directory")


@router.get("/file")
def get_file(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    agent_id: str = Query(...),
    path: str = Query(...),
) -> dict:
    root = _root_for(agent_id, *auth)
    try:
        abs_path = resolve_in_workspace(root, path)
    except WorkspacePathError:
        raise HTTPException(status_code=403, detail="path_outside_workspace")
    try:
        return {"path": path, "content": read_file(abs_path)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="file_not_found")
    except ValueError:
        raise HTTPException(status_code=413, detail="file_too_large")
```

Hinweis: Falls `require_auth` Tupel-Reihenfolge anders ist (z.B. `(user_id, role)`), an bestehende Routes anpassen — Muster aus `projects_git_manage.py` übernehmen.

- [ ] **Step 4: Router registrieren**

In `core/src/hydrahive/api/main.py` bei den anderen `include_router`-Zeilen:
```python
from hydrahive.api.routes.workspace import router as workspace_router
app.include_router(workspace_router)
```

- [ ] **Step 5: Test laufen — muss passen**

Run: `cd core && python -m pytest tests/test_workspace_api.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add core/src/hydrahive/api/routes/workspace.py core/src/hydrahive/api/main.py core/tests/test_workspace_api.py
git commit -m "feat(workspace): API tree + file GET mit Auth + Traversal-Schutz"
```

### Task 8: Workspace-API-Client + useWorkspace-Hook (Frontend)

**Files:**
- Create: `frontend/src/features/chat/workspace/api.ts`
- Create: `frontend/src/features/chat/workspace/useWorkspace.ts`

- [ ] **Step 1: API-Client**

```ts
// frontend/src/features/chat/workspace/api.ts
import { api } from "@/shared/api-client"

export interface TreeEntry { name: string; is_dir: boolean; size: number | null }
export interface FileContent { path: string; content: string }

export const workspaceApi = {
  tree: (agentId: string, path = "") =>
    api.get<TreeEntry[]>(`/workspace/tree?agent_id=${agentId}&path=${encodeURIComponent(path)}`),
  file: (agentId: string, path: string) =>
    api.get<FileContent>(`/workspace/file?agent_id=${agentId}&path=${encodeURIComponent(path)}`),
}
```

- [ ] **Step 2: useWorkspace-Hook**

```ts
// frontend/src/features/chat/workspace/useWorkspace.ts
import { useState, useCallback } from "react"
import { workspaceApi, type FileContent } from "./api"

export function useWorkspace(agentId: string | null) {
  const [openFile, setOpenFile] = useState<FileContent | null>(null)
  const [error, setError] = useState<string | null>(null)

  const open = useCallback(async (path: string) => {
    if (!agentId) return
    setError(null)
    try {
      setOpenFile(await workspaceApi.file(agentId, path))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [agentId])

  return { openFile, setOpenFile, open, error }
}
```

- [ ] **Step 3: Build prüfen**

Run: `cd frontend && npm run build 2>&1 | grep -E "error TS|✓ built"`
Expected: `✓ built`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/chat/workspace/api.ts frontend/src/features/chat/workspace/useWorkspace.ts
git commit -m "feat(workspace): API-Client + useWorkspace-Hook"
```

### Task 9: FileTree + WorkspacePanel-Gerüst (Frontend)

**Files:**
- Create: `frontend/src/features/chat/workspace/FileTree.tsx`
- Create: `frontend/src/features/chat/workspace/WorkspacePanel.tsx`
- Create: `frontend/src/i18n/locales/de/workspace.json`
- Create: `frontend/src/i18n/locales/en/workspace.json`
- Modify: `frontend/src/features/chat/ChatPage.tsx` (Platzhalter ersetzen)

- [ ] **Step 1: i18n-Dateien**

```json
// de/workspace.json
{ "title": "Workspace", "tab_files": "Files", "tab_git": "Git", "tab_editor": "Editor",
  "loading": "Lädt…", "empty": "Leer", "no_file": "Keine Datei geöffnet",
  "no_repo": "Kein Git-Repository", "changed": "{{count}} geändert",
  "commit": "Commit…", "commit_message": "Commit-Nachricht…", "stage_all": "Alle stagen", "save": "Speichern" }
```
```json
// en/workspace.json
{ "title": "Workspace", "tab_files": "Files", "tab_git": "Git", "tab_editor": "Editor",
  "loading": "Loading…", "empty": "Empty", "no_file": "No file open",
  "no_repo": "No Git repository", "changed": "{{count}} changed",
  "commit": "Commit…", "commit_message": "Commit message…", "stage_all": "Stage all", "save": "Save" }
```

- [ ] **Step 2: FileTree**

```tsx
// frontend/src/features/chat/workspace/FileTree.tsx
import { useState, useEffect } from "react"
import { ChevronRight, ChevronDown, File, Folder } from "lucide-react"
import { workspaceApi, type TreeEntry } from "./api"

interface Props { agentId: string; path: string; onOpen: (path: string) => void; depth?: number }

export function FileTree({ agentId, path, onOpen, depth = 0 }: Props) {
  const [entries, setEntries] = useState<TreeEntry[] | null>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  useEffect(() => {
    let alive = true
    workspaceApi.tree(agentId, path).then((e) => { if (alive) setEntries(e) }).catch(() => { if (alive) setEntries([]) })
    return () => { alive = false }
  }, [agentId, path])

  if (entries === null) return <div className="px-2 py-1 text-[10px] text-zinc-600">…</div>

  return (
    <div>
      {entries.map((e) => {
        const childPath = path ? `${path}/${e.name}` : e.name
        const isOpen = expanded.has(e.name)
        return (
          <div key={e.name}>
            <button
              onClick={() => e.is_dir
                ? setExpanded((s) => { const n = new Set(s); n.has(e.name) ? n.delete(e.name) : n.add(e.name); return n })
                : onOpen(childPath)}
              className="w-full flex items-center gap-1 px-1.5 py-0.5 text-[11px] text-zinc-400 hover:bg-white/[4%] rounded text-left"
              style={{ paddingLeft: `${6 + depth * 12}px` }}
            >
              {e.is_dir ? (isOpen ? <ChevronDown size={11} /> : <ChevronRight size={11} />) : <span className="w-[11px]" />}
              {e.is_dir ? <Folder size={11} className="text-violet-400/70" /> : <File size={11} className="text-zinc-500" />}
              <span className="truncate">{e.name}</span>
            </button>
            {e.is_dir && isOpen && <FileTree agentId={agentId} path={childPath} onOpen={onOpen} depth={depth + 1} />}
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 3: WorkspacePanel-Gerüst (nur Files-Tab erstmal)**

```tsx
// frontend/src/features/chat/workspace/WorkspacePanel.tsx
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { FileTree } from "./FileTree"
import { useWorkspace } from "./useWorkspace"

type Tab = "files" | "git" | "editor"

export function WorkspacePanel({ agentId }: { agentId: string | null }) {
  const { t } = useTranslation("workspace")
  const [tab, setTab] = useState<Tab>("files")
  const ws = useWorkspace(agentId)

  if (!agentId) return <div className="p-4 text-[11px] text-zinc-600">{t("no_file")}</div>

  return (
    <div className="flex flex-col h-full">
      <div className="px-2.5 py-2 border-b border-white/[6%] text-[11px] font-medium text-zinc-300">{t("title")}</div>
      <div className="flex border-b border-white/[6%] text-[10px]">
        {(["files", "git", "editor"] as Tab[]).map((id) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex-1 py-1.5 ${tab === id ? "text-violet-300 border-b-2 border-violet-500 bg-violet-500/5" : "text-zinc-500"}`}>
            {t(`tab_${id}`)}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-1">
        {tab === "files" && <FileTree agentId={agentId} path="" onOpen={(p) => { ws.open(p); setTab("editor") }} />}
        {tab === "editor" && <div className="p-2 text-[11px] text-zinc-500">{ws.openFile?.path ?? t("no_file")}</div>}
        {tab === "git" && <div className="p-2 text-[11px] text-zinc-500">{t("no_repo")}</div>}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: In ChatPage Platzhalter ersetzen**

`right`-Slot: `<WorkspacePanel agentId={activeAgent?.id ?? null} />`

- [ ] **Step 5: Build prüfen**

Run: `cd frontend && npm run build 2>&1 | grep -E "error TS|✓ built"`
Expected: `✓ built`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/chat/workspace/ frontend/src/i18n/locales/de/workspace.json frontend/src/i18n/locales/en/workspace.json frontend/src/features/chat/ChatPage.tsx
git commit -m "feat(workspace): FileTree + WorkspacePanel-Gerüst (read-only)"
```

- [ ] **Step 7: Till testet Phase 2**

Push + Deploy. Till prüft: Dateibaum lädt im rechten Panel, Ordner auf-/zuklappbar, Klick auf Datei wechselt zum Editor-Tab und zeigt den Pfad. Kein Pfad-Ausbruch möglich.

---

## Phase 3 — Monaco-Editor (lesen + schreiben)

Ziel: Monaco zeigt Dateiinhalt mit Syntax-Highlighting, speichern via PUT.

### Task 10: Monaco installieren + FileEditor

**Files:**
- Modify: `frontend/package.json` (Monaco)
- Create: `frontend/src/features/chat/workspace/FileEditor.tsx`

- [ ] **Step 1: Monaco installieren**

Run: `cd frontend && npm install @monaco-editor/react`
Expected: `added N packages`

- [ ] **Step 2: FileEditor (dynamic via @monaco-editor/react, lazy)**

```tsx
// frontend/src/features/chat/workspace/FileEditor.tsx
import { lazy, Suspense, useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { Save } from "lucide-react"
import type { FileContent } from "./api"

const Monaco = lazy(() => import("@monaco-editor/react"))

function langFromPath(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase()
  const map: Record<string, string> = {
    ts: "typescript", tsx: "typescript", js: "javascript", jsx: "javascript",
    py: "python", json: "json", md: "markdown", css: "css", html: "html",
    sh: "shell", yml: "yaml", yaml: "yaml", toml: "ini", rs: "rust", go: "go",
  }
  return map[ext ?? ""] ?? "plaintext"
}

interface Props { file: FileContent; onSave: (content: string) => Promise<void> }

export function FileEditor({ file, onSave }: Props) {
  const { t } = useTranslation("workspace")
  const [value, setValue] = useState(file.content)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => { setValue(file.content); setDirty(false) }, [file.path, file.content])

  async function save() {
    setSaving(true)
    try { await onSave(value); setDirty(false) } finally { setSaving(false) }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-2 py-1 border-b border-white/[6%]">
        <span className="text-[10px] text-zinc-400 truncate flex-1 font-mono">{file.path}{dirty ? " •" : ""}</span>
        <button onClick={save} disabled={!dirty || saving}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-violet-500/15 text-violet-300 disabled:opacity-40">
          <Save size={10} /> {t("save")}
        </button>
      </div>
      <div className="flex-1 min-h-0">
        <Suspense fallback={<div className="p-2 text-[11px] text-zinc-600">{t("loading")}</div>}>
          <Monaco
            height="100%" theme="vs-dark" language={langFromPath(file.path)} value={value}
            onChange={(v) => { setValue(v ?? ""); setDirty(true) }}
            options={{ fontSize: 12, minimap: { enabled: false }, scrollBeyondLastLine: false }}
          />
        </Suspense>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Build prüfen**

Run: `cd frontend && npm run build 2>&1 | grep -E "error TS|✓ built"`
Expected: `✓ built` (Bundle-Warnung wegen Monaco ist ok)

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/features/chat/workspace/FileEditor.tsx
git commit -m "feat(workspace): Monaco FileEditor (lazy) mit Syntax-Highlighting"
```

### Task 11: PUT /file Backend + Speichern verdrahten

**Files:**
- Modify: `core/src/hydrahive/workspace/_tree.py` (write_file)
- Modify: `core/src/hydrahive/api/routes/workspace.py` (PUT)
- Modify: `frontend/src/features/chat/workspace/api.ts` + `useWorkspace.ts` + `WorkspacePanel.tsx`
- Test: `core/tests/test_workspace_api.py`

- [ ] **Step 1: write_file im Backend**

In `_tree.py` ergänzen:
```python
def write_file(abs_path: Path, content: str) -> None:
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
```

- [ ] **Step 2: Failing test**

In `test_workspace_api.py`:
```python
def test_write_and_read_file(client, admin_headers):
    agent = _agent(client, admin_headers)
    aid = agent["id"]
    res = client.put("/api/workspace/file", headers=admin_headers,
                     json={"agent_id": aid, "path": "note.txt", "content": "hallo"})
    assert res.status_code == 200, res.text
    got = client.get(f"/api/workspace/file?agent_id={aid}&path=note.txt", headers=admin_headers)
    assert got.json()["content"] == "hallo"


def test_write_rejects_traversal(client, admin_headers):
    agent = _agent(client, admin_headers)
    res = client.put("/api/workspace/file", headers=admin_headers,
                     json={"agent_id": agent["id"], "path": "../escape.txt", "content": "x"})
    assert res.status_code == 403
```

- [ ] **Step 3: Test laufen — muss fehlschlagen**

Run: `cd core && python -m pytest tests/test_workspace_api.py::test_write_and_read_file -v`
Expected: FAIL (405/404, PUT existiert nicht)

- [ ] **Step 4: PUT-Endpunkt**

In `workspace.py`:
```python
from pydantic import BaseModel
from hydrahive.workspace._tree import write_file

class WriteBody(BaseModel):
    agent_id: str
    path: str
    content: str

@router.put("/file")
def put_file(
    body: WriteBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    root = _root_for(body.agent_id, *auth)
    try:
        abs_path = resolve_in_workspace(root, body.path)
    except WorkspacePathError:
        raise HTTPException(status_code=403, detail="path_outside_workspace")
    write_file(abs_path, body.content)
    return {"ok": True}
```

- [ ] **Step 5: Test laufen — muss passen**

Run: `cd core && python -m pytest tests/test_workspace_api.py -v`
Expected: PASS (alle)

- [ ] **Step 6: Frontend verdrahten**

`api.ts`:
```ts
  save: (agentId: string, path: string, content: string) =>
    api.put<{ ok: boolean }>(`/workspace/file`, { agent_id: agentId, path, content }),
```
`useWorkspace.ts` — `save`-Callback ergänzen:
```ts
  const save = useCallback(async (content: string) => {
    if (!agentId || !openFile) return
    await workspaceApi.save(agentId, openFile.path, content)
    setOpenFile({ ...openFile, content })
  }, [agentId, openFile])
```
und `save` returnen. In `WorkspacePanel.tsx` Editor-Tab:
```tsx
{tab === "editor" && ws.openFile && <FileEditor file={ws.openFile} onSave={ws.save} />}
{tab === "editor" && !ws.openFile && <div className="p-2 text-[11px] text-zinc-500">{t("no_file")}</div>}
```

- [ ] **Step 7: Build prüfen**

Run: `cd frontend && npm run build 2>&1 | grep -E "error TS|✓ built"`
Expected: `✓ built`

- [ ] **Step 8: Commit**

```bash
git add core/src/hydrahive/workspace/_tree.py core/src/hydrahive/api/routes/workspace.py core/tests/test_workspace_api.py frontend/src/features/chat/workspace/
git commit -m "feat(workspace): Datei speichern (PUT) + Editor verdrahtet"
```

- [ ] **Step 9: Till testet Phase 3**

Push + Deploy. Till prüft: Datei öffnen zeigt Monaco mit Highlighting, bearbeiten setzt Dirty-Marker, Speichern persistiert, Traversal beim Schreiben blockiert.

---

## Phase 4 — Git-Integration

Ziel: Status, Diff, Stage, Commit aus dem Git-Panel.

### Task 12: Git-Status/Diff/Stage/Commit (Backend)

**Files:**
- Create: `core/src/hydrahive/workspace/_git_status.py`
- Modify: `core/src/hydrahive/api/routes/workspace.py`
- Test: `core/tests/test_workspace_api.py`

- [ ] **Step 1: Git-Helfer**

```python
# core/src/hydrahive/workspace/_git_status.py
from __future__ import annotations
import subprocess
from pathlib import Path


def _git(root: Path, *args: str) -> str:
    res = subprocess.run(["git", "-C", str(root), *args],
                         capture_output=True, text=True, timeout=15)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or "git_error")
    return res.stdout


def is_repo(root: Path) -> bool:
    return (root / ".git").exists()


def status(root: Path) -> dict:
    if not is_repo(root):
        return {"is_repo": False, "branch": None, "files": []}
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    out = _git(root, "status", "--porcelain")
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        code, name = line[:2], line[3:]
        files.append({"status": code.strip(), "path": name, "staged": code[0] != " " and code[0] != "?"})
    return {"is_repo": True, "branch": branch, "files": files}


def diff(root: Path, file: str) -> str:
    return _git(root, "diff", "HEAD", "--", file)


def stage(root: Path, file: str, staged: bool) -> None:
    _git(root, "add" if staged else "reset", "HEAD" if not staged else "--", file) if not staged else _git(root, "add", "--", file)


def commit(root: Path, message: str) -> str:
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD").strip()
```

Hinweis Step: `stage()` korrekt:
```python
def stage(root: Path, file: str, staged: bool) -> None:
    if staged:
        _git(root, "add", "--", file)
    else:
        _git(root, "reset", "HEAD", "--", file)
```
(die Einzeiler-Version oben verwerfen — diese nehmen.)

- [ ] **Step 2: Failing test**

```python
def test_git_status_no_repo(client, admin_headers):
    agent = _agent(client, admin_headers)
    res = client.get(f"/api/workspace/git/status?agent_id={agent['id']}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["is_repo"] is False
```

- [ ] **Step 3: Test laufen — muss fehlschlagen**

Run: `cd core && python -m pytest tests/test_workspace_api.py::test_git_status_no_repo -v`
Expected: FAIL (404)

- [ ] **Step 4: Endpunkte**

```python
from hydrahive.workspace import _git_status as gs

@router.get("/git/status")
def git_status(auth: Annotated[tuple[str, str], Depends(require_auth)], agent_id: str = Query(...)) -> dict:
    root = _root_for(agent_id, *auth)
    return gs.status(root)

@router.get("/git/diff")
def git_diff(auth: Annotated[tuple[str, str], Depends(require_auth)], agent_id: str = Query(...), file: str = Query(...)) -> dict:
    root = _root_for(agent_id, *auth)
    try:
        resolve_in_workspace(root, file)
    except WorkspacePathError:
        raise HTTPException(status_code=403, detail="path_outside_workspace")
    return {"diff": gs.diff(root, file)}

class StageBody(BaseModel):
    agent_id: str
    file: str
    staged: bool

@router.post("/git/stage")
def git_stage(body: StageBody, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    root = _root_for(body.agent_id, *auth)
    try:
        resolve_in_workspace(root, body.file)
    except WorkspacePathError:
        raise HTTPException(status_code=403, detail="path_outside_workspace")
    gs.stage(root, body.file, body.staged)
    return {"ok": True}

class CommitBody(BaseModel):
    agent_id: str
    message: str

@router.post("/git/commit")
def git_commit(body: CommitBody, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="empty_message")
    root = _root_for(body.agent_id, *auth)
    try:
        return {"sha": gs.commit(root, body.message)}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 5: Test laufen — muss passen**

Run: `cd core && python -m pytest tests/test_workspace_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add core/src/hydrahive/workspace/_git_status.py core/src/hydrahive/api/routes/workspace.py core/tests/test_workspace_api.py
git commit -m "feat(workspace): Git status/diff/stage/commit Endpunkte (workspace-scoped)"
```

### Task 13: GitPanel (Frontend)

**Files:**
- Modify: `frontend/src/features/chat/workspace/api.ts`
- Create: `frontend/src/features/chat/workspace/GitPanel.tsx`
- Modify: `frontend/src/features/chat/workspace/WorkspacePanel.tsx`

- [ ] **Step 1: API-Client erweitern**

```ts
export interface GitFile { status: string; path: string; staged: boolean }
export interface GitStatus { is_repo: boolean; branch: string | null; files: GitFile[] }

export const gitApi = {
  status: (agentId: string) => api.get<GitStatus>(`/workspace/git/status?agent_id=${agentId}`),
  diff: (agentId: string, file: string) => api.get<{ diff: string }>(`/workspace/git/diff?agent_id=${agentId}&file=${encodeURIComponent(file)}`),
  stage: (agentId: string, file: string, staged: boolean) => api.post(`/workspace/git/stage`, { agent_id: agentId, file, staged }),
  commit: (agentId: string, message: string) => api.post<{ sha: string }>(`/workspace/git/commit`, { agent_id: agentId, message }),
}
```

- [ ] **Step 2: GitPanel**

```tsx
// frontend/src/features/chat/workspace/GitPanel.tsx
import { useState, useEffect, useCallback } from "react"
import { useTranslation } from "react-i18next"
import { gitApi, type GitStatus } from "./api"

export function GitPanel({ agentId }: { agentId: string }) {
  const { t } = useTranslation("workspace")
  const [status, setStatus] = useState<GitStatus | null>(null)
  const [message, setMessage] = useState("")
  const [diff, setDiff] = useState<string | null>(null)

  const refresh = useCallback(() => {
    gitApi.status(agentId).then(setStatus).catch(() => setStatus(null))
  }, [agentId])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 4000)
    return () => clearInterval(id)
  }, [refresh])

  if (!status) return <div className="p-2 text-[11px] text-zinc-600">{t("loading")}</div>
  if (!status.is_repo) return <div className="p-2 text-[11px] text-zinc-600">{t("no_repo")}</div>

  return (
    <div className="flex flex-col h-full text-[11px]">
      <div className="px-2 py-1.5 border-b border-white/[6%] flex items-center gap-2">
        <span className="text-emerald-400">⎇ {status.branch}</span>
        <span className="text-zinc-500 ml-auto">{t("changed", { count: status.files.length })}</span>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto">
        {status.files.map((f) => (
          <div key={f.path} className="flex items-center gap-1.5 px-2 py-1 hover:bg-white/[3%]">
            <input type="checkbox" checked={f.staged} className="accent-violet-500"
              onChange={(e) => gitApi.stage(agentId, f.path, e.target.checked).then(refresh)} />
            <span className={`font-mono ${f.status === "M" ? "text-amber-400" : f.status === "??" ? "text-emerald-400" : "text-zinc-400"}`}>{f.status || "·"}</span>
            <button onClick={() => gitApi.diff(agentId, f.path).then((r) => setDiff(r.diff))}
              className="truncate text-zinc-400 hover:text-zinc-200 text-left flex-1">{f.path}</button>
          </div>
        ))}
      </div>
      {diff !== null && (
        <pre className="max-h-40 overflow-auto px-2 py-1 text-[10px] font-mono bg-black/30 border-t border-white/[6%] text-zinc-400 whitespace-pre-wrap">{diff || "—"}</pre>
      )}
      <div className="border-t border-white/[6%] p-2 flex flex-col gap-1.5">
        <input value={message} onChange={(e) => setMessage(e.target.value)} placeholder={t("commit_message")}
          className="bg-zinc-900 border border-white/[8%] rounded px-2 py-1 text-[10px] text-zinc-200" />
        <button disabled={!message.trim() || !status.files.some((f) => f.staged)}
          onClick={() => gitApi.commit(agentId, message).then(() => { setMessage(""); setDiff(null); refresh() })}
          className="px-2 py-1 rounded bg-violet-500/15 text-violet-300 text-[10px] disabled:opacity-40">
          {t("commit")}
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: In WorkspacePanel einbinden**

Git-Tab: `{tab === "git" && <GitPanel agentId={agentId} />}`

- [ ] **Step 4: Build prüfen**

Run: `cd frontend && npm run build 2>&1 | grep -E "error TS|✓ built"`
Expected: `✓ built`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/chat/workspace/
git commit -m "feat(workspace): GitPanel — Status, Diff, Stage, Commit"
```

- [ ] **Step 6: Till testet Phase 4**

Push + Deploy. Till prüft: Git-Tab zeigt geänderte Dateien + Branch, Diff-Klick zeigt Diff, Checkbox staged, Commit mit Message funktioniert, leere Message blockiert.

---

## Phase 5 — Politur

### Task 14: Git-Marker im FileTree + Security-Review

**Files:**
- Modify: `frontend/src/features/chat/workspace/FileTree.tsx`
- Modify: `frontend/src/features/chat/workspace/WorkspacePanel.tsx`

- [ ] **Step 1: Git-Status an FileTree durchreichen**

WorkspacePanel hält den Git-Status (aus GitPanel hochziehen in useWorkspace oder gemeinsames Polling). FileTree bekommt `Map<path, status>` und zeigt M/A-Marker rechts neben Dateinamen. (Konkret: `useWorkspace` um `gitStatus` + Polling erweitern, an beide Panels geben.)

- [ ] **Step 2: Build prüfen**

Run: `cd frontend && npm run build 2>&1 | grep -E "error TS|✓ built"`
Expected: `✓ built`

- [ ] **Step 3: Security-Review (PFLICHT)**

Dispatch security-reviewer agent auf `core/src/hydrahive/workspace/` + `api/routes/workspace.py`. Fokus: Path-Traversal, Symlink-Ausbruch, fehlende Owner-Checks, Command-Injection in `_git`. CRITICAL/HIGH vor Merge fixen.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/chat/workspace/
git commit -m "feat(workspace): Git-Marker im FileTree"
```

### Task 15: Mobile-Fallback + finaler Test

**Files:**
- Modify: `frontend/src/features/chat/layout/ThreePanelLayout.tsx`

- [ ] **Step 1: Mobile-Verhalten**

Auf schmalen Viewports (`md:` breakpoint) Seitenpanels standardmäßig zu, Chat voll. Panels öffnen als Overlay statt fester Spalte. Tailwind: `hidden md:flex` für die Panels im offenen Zustand, plus ein mobiler Toggle.

- [ ] **Step 2: Build + Commit**

```bash
cd frontend && npm run build 2>&1 | grep -E "error TS|✓ built"
git add frontend/src/features/chat/layout/ThreePanelLayout.tsx
git commit -m "feat(chat): Mobile-Fallback für 3-Panel-Layout"
```

- [ ] **Step 3: Till testet final**

Push + Deploy. Voller Durchlauf: Desktop 3 Panels + Kollaps, Datei browsen/editieren/speichern, Git committen, mobil sauberer Fallback, Buddy unverändert.

---

## Self-Review-Ergebnis

- **Spec-Abdeckung:** Alle 5 Phasen + 7 API-Endpunkte + Pfad-Validierung + Monaco + Git-Umfang (Status/Diff/Stage/Commit) + Kollaps-Persistenz + i18n + Mobile abgedeckt.
- **Sicherheit:** Pfad-Validierung als eigener getesteter Task (5), Security-Review als Pflicht-Gate (Task 14).
- **Buddy:** Wird nicht angefasst — nur `chat/`-Feature.
- **Offener Punkt fürs Ausführen:** `require_auth`-Tupel-Reihenfolge (`(user_id, role)` vs. anders) beim ersten Backend-Task an bestehende Routes angleichen.
