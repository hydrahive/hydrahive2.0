# Notizbuch-Modul v1 — Implementierungsplan (erstes echtes Modul, Hub-Repo)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans, Task für Task. Steps mit Checkbox (`- [ ]`).
>
> **Hinweis zur Verifikation:** Dieses Modul lebt in seinem EIGENEN Repo (`hydrahive2-modules`), nicht im HydraHive2-Core-Repo → **kein In-Repo-pytest** (Tills Design-Entscheidung „design-rein"). Verifikation: Frontend-Build-Check (temporär in den Core-Build kopieren), dann Install auf `.23` + server-seitiger curl-Smoke (inkl. Zwei-User-Isolation) + Tills Browser-E2E. Die „Tests" sind hier Build-Check + curl-Smoke, kein RED-GREEN-Unit-Zyklus.

**Goal:** Ein Notizbuch-Modul (Notizen mit Titel + Markdown-Body, CRUD, pro User privat) im Hub-Repo, installierbar per Knopf.

**Architecture:** Standard-Modul nach dem SP1-Vertrag (`manifest`+`backend/register(ctx)`+`migrations`+`frontend/{index,NotizbuchPage}`), entwickelt in einem Klon von `hydrahive2-modules`, gepusht, auf `.23` installiert. Backend = CRUD-Router unter `/api/modules/notizbuch`, ownership-strikt per `require_auth`-User. Frontend = Liste+Editor+Markdown-Vorschau, nutzt nur Core-Deps.

**Tech Stack:** Python/FastAPI (Modul-Backend, läuft im HH2-Prozess) · React+TS (in den Core-Vite-Build kompiliert) · `react-markdown` (vorhandene Core-Dep) · git (Hub-Repo).

**Spec:** `docs/superpowers/specs/2026-06-04-notizbuch-modul-design.md`.

---

## Arbeitsorte
- **Modul-Code:** Klon von `hydrahive2-modules` unter `/home/till/hydrahive2-modules` (Task 1 legt ihn an). Alle Modul-Dateien dort.
- **Frontend-Build-Check:** der HH2-Core-Repo `/home/till/claudeneu` (temporär kopieren, bauen, aufräumen).
- **Verifikation:** Testserver `.23` (`ssh joshua@192.168.3.23`, git/build als `sudo -u hydrahive`, restart als `sudo systemctl`).

## Verifizierte Vorlagen
- Modul-Vertrag: `docs/feature-map/28-modules.md`; Skelett: `modules/example/` (im HH2-Repo) + das `example/` im Hub-Repo.
- Auth → User: `auth: Annotated[tuple[str, str], Depends(require_auth)]` dann `user, _ = auth` (`api/routes/scratchpad.py:22`).
- 404: `from hydrahive.api.middleware.errors import coded` → `raise coded(status.HTTP_404_NOT_FOUND, "note_not_found")`.
- DB: `from hydrahive.db.connection import db` → `with db() as c:`, `dict(row)` (sqlite3.Row), parametrisiert.
- Markdown: `react-markdown` ist Core-Dep (`frontend/package.json`); direkt nutzbar (`import ReactMarkdown from "react-markdown"`).
- Hub-Format: `hub.json` = `{"modules":[{"id","name","path"}]}`; Install zieht `path` aus dem geklonten Hub-Cache.

---

## Task 1: Hub-Klon + Modul-Gerüst

**Files (im Hub-Repo-Klon):** `/home/till/hydrahive2-modules/notizbuch/manifest.json` · `…/hub.json` (ergänzen)

- [ ] **Step 1:** Hub-Repo klonen (falls noch nicht da):
```bash
[ -d /home/till/hydrahive2-modules/.git ] || git clone git@github.com:hydrahive/hydrahive2-modules.git /home/till/hydrahive2-modules
cd /home/till/hydrahive2-modules && git pull --ff-only && ls
```
Erwartung: enthält `example/` + `hub.json`.
- [ ] **Step 2:** Modul-Verzeichnisse + Manifest anlegen:
```bash
mkdir -p /home/till/hydrahive2-modules/notizbuch/backend /home/till/hydrahive2-modules/notizbuch/migrations /home/till/hydrahive2-modules/notizbuch/frontend
```
`notizbuch/manifest.json`:
```json
{
  "id": "notizbuch",
  "name": "Notizbuch",
  "version": "1.0.0",
  "icon": "NotebookPen",
  "nav_group": "working",
  "permissions": [],
  "has_service": false,
  "min_core_version": "2.0.0"
}
```
- [ ] **Step 3:** `hub.json` um den Notizbuch-Eintrag ergänzen (vorhandenen `example`-Eintrag behalten):
```json
{
  "modules": [
    { "id": "example", "name": "Beispiel-Modul", "path": "example" },
    { "id": "notizbuch", "name": "Notizbuch", "path": "notizbuch" }
  ]
}
```
- [ ] **Step 4:** Verify: `python3 -c "import json; d=json.load(open('/home/till/hydrahive2-modules/hub.json')); print([m['id'] for m in d['modules']])"` → `['example', 'notizbuch']`. `python3 -c "import json; json.load(open('/home/till/hydrahive2-modules/notizbuch/manifest.json'))"` → kein Fehler.
- [ ] **Step 5:** (noch nicht committen — gesammelt in Task 7.)

---

## Task 2: Migration

**Files:** `/home/till/hydrahive2-modules/notizbuch/migrations/001_notizbuch.sql`

- [ ] **Step 1:** Datei schreiben:
```sql
CREATE TABLE IF NOT EXISTS module_notizbuch_notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"      TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_module_notizbuch_notes_user ON module_notizbuch_notes("user");
```
- [ ] **Step 2:** Verify SQL parst: `python3 -c "import sqlite3; c=sqlite3.connect(':memory:'); c.executescript(open('/home/till/hydrahive2-modules/notizbuch/migrations/001_notizbuch.sql').read()); print([r[1] for r in c.execute('PRAGMA table_info(module_notizbuch_notes)')])"` → `['id','user','title','body','created_at','updated_at']`.

---

## Task 3: Backend — CRUD, ownership-strikt

**Files:** `/home/till/hydrahive2-modules/notizbuch/backend/__init__.py`

- [ ] **Step 1:** Datei schreiben:
```python
"""Notizbuch-Modul Backend — Notizen pro User (CRUD), ownership-strikt.

register(ctx) → Router (/api/modules/notizbuch/...) + Migrationen. Jede Notiz
gehört dem anlegenden User (require_auth); fremde Notizen sind unsichtbar/404.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

router = APIRouter()

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


class NoteIn(BaseModel):
    title: str = Field(default="", max_length=500)
    body: str = Field(default="", max_length=1_000_000)


@router.get("/notes")
def list_notes(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    user, _ = auth
    with db() as c:
        return [
            dict(r) for r in c.execute(
                'SELECT id, title, updated_at FROM module_notizbuch_notes '
                'WHERE "user" = ? ORDER BY updated_at DESC',
                (user,),
            ).fetchall()
        ]


@router.get("/notes/{note_id}")
def get_note(note_id: int, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    with db() as c:
        row = c.execute(
            'SELECT id, title, body, created_at, updated_at FROM module_notizbuch_notes '
            'WHERE id = ? AND "user" = ?',
            (note_id, user),
        ).fetchone()
    if row is None:
        raise coded(status.HTTP_404_NOT_FOUND, "note_not_found")
    return dict(row)


@router.post("/notes")
def create_note(body: NoteIn, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    with db() as c:
        cur = c.execute(
            'INSERT INTO module_notizbuch_notes ("user", title, body) VALUES (?, ?, ?)',
            (user, body.title, body.body),
        )
        row = c.execute(
            'SELECT id, title, body, created_at, updated_at FROM module_notizbuch_notes WHERE id = ?',
            (cur.lastrowid,),
        ).fetchone()
    return dict(row)


@router.put("/notes/{note_id}")
def update_note(note_id: int, body: NoteIn,
                auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    with db() as c:
        cur = c.execute(
            f'UPDATE module_notizbuch_notes SET title = ?, body = ?, updated_at = {_NOW} '
            'WHERE id = ? AND "user" = ?',
            (body.title, body.body, note_id, user),
        )
        if cur.rowcount == 0:
            raise coded(status.HTTP_404_NOT_FOUND, "note_not_found")
        row = c.execute(
            'SELECT id, title, body, created_at, updated_at FROM module_notizbuch_notes WHERE id = ?',
            (note_id,),
        ).fetchone()
    return dict(row)


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    with db() as c:
        cur = c.execute(
            'DELETE FROM module_notizbuch_notes WHERE id = ? AND "user" = ?',
            (note_id, user),
        )
        if cur.rowcount == 0:
            raise coded(status.HTTP_404_NOT_FOUND, "note_not_found")
    return {"ok": True}


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
```
- [ ] **Step 2:** Syntax-Check: `python3 -c "import ast; ast.parse(open('/home/till/hydrahive2-modules/notizbuch/backend/__init__.py').read()); print('syntax ok')"`. (Echte Ausführung erst beim Install auf `.23` — `hydrahive.*` ist im Hub-Klon nicht vorhanden, das ist erwartet.)

---

## Task 4: Frontend index.tsx (Vertrag)

**Files:** `/home/till/hydrahive2-modules/notizbuch/frontend/index.tsx`

- [ ] **Step 1:** Datei schreiben:
```tsx
import { NotizbuchPage } from "./NotizbuchPage"

export const routes = [{ path: "/notizbuch", element: <NotizbuchPage /> }]
export const nav = [
  { path: "/notizbuch", icon: "NotebookPen", labelKey: "notizbuch", group: "working", roles: [] },
]
export const i18n = {
  de: { notizbuch: {
    title: "Notizbuch", new: "Neue Notiz", titlePlaceholder: "Titel",
    bodyPlaceholder: "Markdown …", save: "Speichern", delete: "Löschen",
    preview: "Vorschau", edit: "Bearbeiten", empty: "Noch keine Notizen", untitled: "Unbenannt",
  } },
  en: { notizbuch: {
    title: "Notebook", new: "New note", titlePlaceholder: "Title",
    bodyPlaceholder: "Markdown …", save: "Save", delete: "Delete",
    preview: "Preview", edit: "Edit", empty: "No notes yet", untitled: "Untitled",
  } },
}
```
- [ ] **Step 2:** (Build-Check in Task 6.)

---

## Task 5: Frontend NotizbuchPage.tsx

**Files:** `/home/till/hydrahive2-modules/notizbuch/frontend/NotizbuchPage.tsx`

> Lies zuerst (im HH2-Repo) `frontend/src/shared/api-client.ts` (Methoden-Namen: `get`/`post`/`put` + ob `del` oder `delete`) und `frontend/src/features/llm/DefaultModelsSection.tsx` (Stil: useState/useEffect, Fehleranzeige, i18n via `useTranslation`). Passe die api-Methoden-Namen an die echten an.

- [ ] **Step 1:** `NotizbuchPage.tsx` schreiben — zweispaltig (Liste links, Editor rechts), CRUD + Markdown-Vorschau, nur Core-Deps:
```tsx
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import ReactMarkdown from "react-markdown"
import { api } from "@/shared/api-client"

interface NoteListItem { id: number; title: string; updated_at: string }
interface Note { id: number; title: string; body: string; created_at: string; updated_at: string }

const BASE = "/modules/notizbuch"

export function NotizbuchPage() {
  const { t } = useTranslation("notizbuch")
  const [list, setList] = useState<NoteListItem[]>([])
  const [active, setActive] = useState<Note | null>(null)
  const [preview, setPreview] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadList = () => api.get<NoteListItem[]>(`${BASE}/notes`).then(setList).catch((e) => setError(String(e)))
  useEffect(() => { loadList() }, [])

  async function open(id: number) {
    setError(null)
    try { setActive(await api.get<Note>(`${BASE}/notes/${id}`)); setPreview(false) }
    catch (e) { setError(String(e)) }
  }
  async function createNote() {
    setError(null)
    try {
      const note = await api.post<Note>(`${BASE}/notes`, { title: "", body: "" })
      setActive(note); setPreview(false); await loadList()
    } catch (e) { setError(String(e)) }
  }
  async function save() {
    if (!active) return
    setError(null)
    try {
      const updated = await api.put<Note>(`${BASE}/notes/${active.id}`, { title: active.title, body: active.body })
      setActive(updated); await loadList()
    } catch (e) { setError(String(e)) }
  }
  async function remove() {
    if (!active) return
    setError(null)
    try { await api.del(`${BASE}/notes/${active.id}`); setActive(null); await loadList() }
    catch (e) { setError(String(e)) }
  }

  return (
    <div className="flex gap-4 h-full">
      <aside className="w-64 shrink-0 space-y-2">
        <button onClick={createNote} className="w-full px-3 py-2 rounded-lg bg-violet-500/15 text-violet-300 text-sm hover:bg-violet-500/25">
          + {t("new")}
        </button>
        {list.length === 0 && <p className="text-zinc-600 text-sm py-2">{t("empty")}</p>}
        {list.map((n) => (
          <button key={n.id} onClick={() => open(n.id)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate ${active?.id === n.id ? "bg-white/10 text-zinc-100" : "text-zinc-400 hover:bg-white/5"}`}>
            {n.title || t("untitled")}
          </button>
        ))}
      </aside>
      <section className="flex-1 min-w-0">
        {error && <div className="mb-3 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">{error}</div>}
        {active ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <input value={active.title} placeholder={t("titlePlaceholder")}
                onChange={(e) => setActive({ ...active, title: e.target.value })}
                className="flex-1 px-3 py-2 rounded-lg bg-zinc-900 border border-white/10 text-zinc-100" />
              <button onClick={() => setPreview((p) => !p)} className="px-3 py-2 rounded-lg text-sm text-zinc-300 hover:bg-white/5">
                {preview ? t("edit") : t("preview")}
              </button>
              <button onClick={save} className="px-3 py-2 rounded-lg text-sm bg-violet-500/20 text-violet-200 hover:bg-violet-500/30">{t("save")}</button>
              <button onClick={remove} className="px-3 py-2 rounded-lg text-sm text-rose-300 hover:bg-rose-500/10">{t("delete")}</button>
            </div>
            {preview
              ? <div className="prose prose-invert max-w-none p-3 rounded-lg bg-zinc-900/50 border border-white/5"><ReactMarkdown>{active.body}</ReactMarkdown></div>
              : <textarea value={active.body} placeholder={t("bodyPlaceholder")}
                  onChange={(e) => setActive({ ...active, body: e.target.value })}
                  className="w-full h-[60vh] px-3 py-2 rounded-lg bg-zinc-900 border border-white/10 text-zinc-100 font-mono text-sm" />}
          </div>
        ) : <p className="text-zinc-600 text-sm">{t("empty")}</p>}
      </section>
    </div>
  )
}
```
> Falls der api-Client `delete` statt `del` heißt (beim Lesen prüfen), entsprechend ersetzen. Falls `prose`-Klassen (Tailwind-Typography) nicht verfügbar sind, ist das nur Styling — der `<ReactMarkdown>` rendert trotzdem; im Zweifel die `prose`-Klassen weglassen.

---

## Task 6: Frontend-Build-Check (im Core-Build, temporär)

**Files:** keine bleibenden — temporäre Kopie im HH2-Repo

- [ ] **Step 1:** Modul-Frontend temporär in den Core-Build kopieren + bauen (Muster aus Modul-SP1-T14):
```bash
cd /home/till/claudeneu/frontend
cp -r /home/till/hydrahive2-modules/notizbuch/frontend src/modules/notizbuch
node scripts/gen-modules.mjs   # nimmt notizbuch in index.generated.ts auf
npm run build 2>&1 | tail -4
npx eslint src/modules/notizbuch 2>&1 | tail -10
```
Erwartung: `npm run build` grün (das Notizbuch-Frontend kompiliert + integriert mit den Core-Hooks), eslint ohne neue Fehler.
- [ ] **Step 2:** Aufräumen (Modul gehört NICHT in den Core-Repo):
```bash
cd /home/till/claudeneu/frontend
rm -rf src/modules/notizbuch src/modules/index.generated.ts
cd /home/till/claudeneu && git status --porcelain | grep -i "src/modules" && echo "LEAK!" || echo "clean — nichts im Core-Repo"
```
Erwartung: `clean`. (Falls `src/modules/index.generated.ts` als modifiziert auftaucht: es ist gitignored → ok.)

---

## Task 7: Publish in den Hub

**Files:** Commit im Hub-Repo `/home/till/hydrahive2-modules`

- [ ] **Step 1:** Im Hub-Repo committen + pushen:
```bash
cd /home/till/hydrahive2-modules
git add -A && git -c user.name="tilleulenspiegel" -c user.email="eulenspiegel41@gmail.com" commit -m "feat: Notizbuch-Modul (Notizen pro User, Markdown, CRUD)"
git push origin main 2>&1 | tail -3
```
- [ ] **Step 2:** Verify aus der Ferne installierbar: `GIT_TERMINAL_PROMPT=0 git ls-remote https://github.com/hydrahive/hydrahive2-modules.git 2>&1 | head -2` → kein Fehler; und `curl -s https://raw.githubusercontent.com/hydrahive/hydrahive2-modules/main/hub.json | python3 -c "import sys,json;print([m['id'] for m in json.load(sys.stdin)['modules']])"` → enthält `notizbuch`.

---

## Task 8: Install auf `.23` + server-seitiger Smoke (inkl. Zwei-User-Isolation)

**Verify auf dem Testserver** (controller; `.23` läuft auf main mit Modulsystem).

- [ ] **Step 1:** Auf `.23` über die Admin-API installieren (Modul-Knopf-Äquivalent), Stream abwarten:
```bash
ssh joshua@192.168.3.23 'TOK=$(curl -s -X POST http://127.0.0.1:8001/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"claudetest\",\"password\":\"Lhx9-teamtest-2026\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)[\"access_token\"])"); curl -s -X POST http://127.0.0.1:8001/api/admin/modules/notizbuch/install -H "Authorization: Bearer $TOK" | tail -5'
```
Dann ~10s warten (Build+Restart), Backend `active` prüfen.
- [ ] **Step 2:** **CRUD-Smoke als claudetest:** POST /api/modules/notizbuch/notes (title+body) → 200 mit id; GET /notes → enthält die Notiz; GET /notes/{id} → voller body; PUT /notes/{id} → geänderter Titel; GET /notes/{id} → Änderung da; DELETE /notes/{id} → ok; GET /notes → leer.
- [ ] **Step 3:** **Zwei-User-Isolation:** als claudetest eine Notiz anlegen (id X). Dann als zweiter User (z.B. `bibitest`/`Bibi-Test!2026`): GET /notes → enthält X NICHT; GET /notes/{X} → **404**; PUT /notes/{X} → **404**; DELETE /notes/{X} → **404**. (Beweis: ownership-strikt, kein IDOR.)
- [ ] **Step 4:** Migration/Loader: `journalctl -u hydrahive2` → „Modul 'notizbuch' geladen" + Migration angewandt; `module_schema_version` hat einen notizbuch-Eintrag.

---

## Task 9: Browser-E2E (Till) + Abschluss

- [ ] **Step 1:** Till: „Notizbuch" erscheint im Nav → Notiz anlegen (Titel + Markdown) → **Vorschau** rendert das Markdown → bearbeiten/speichern → löschen → nach Reload korrekt → **deinstallieren** → weg → **re-install** → Notizen wieder da (Daten-bleiben).
- [ ] **Step 2:** Nach Tills OK: Memory + ROADMAP nachziehen (Notizbuch = erstes echtes Modul fertig; Modul-Standard „eigenes Repo" etabliert).

---

## Offene Detailpunkte (beim Bau zu prüfen, kein Blocker)
- api-Client-Methode für DELETE (`api.del` vs `api.delete`) — beim Lesen von `frontend/src/shared/api-client.ts` bestätigen.
- Tailwind-`prose`-Klassen vorhanden? Falls nicht, weglassen (nur Styling; ReactMarkdown rendert trotzdem).
- `NotebookPen` ist ein gültiger lucide-Icon-Name (Resolver-Fallback `Boxes`, falls nicht) — beim Bau ein Blick in lucide-react genügt.
- `.23`-Install des Frontend-Builds: der Modul-Install baut das Frontend auf dem Server neu (npm run build) — dauert; Stream/Restart abwarten.
