# Notizbuch-Modul v1 — Design (erstes echtes Modul)

> **Ziel:** Das erste *echte* Modul (über das `example`-Skelett hinaus) — ein **Notizbuch**:
> Notizen mit Titel + Markdown-Body, volles CRUD, **pro User privat**. Lebt design-rein in
> seinem eigenen Repo (dem Modul-Hub), nicht im Core. Beweist das Modulsystem an einer echten App
> und setzt den Standard „echtes Modul = eigenes Repo".
>
> **Voraussetzung:** Modulsystem v1 auf main (`docs/feature-map/28-modules.md`). Hub-Repo
> `hydrahive2-modules` (GitHub, first-party) existiert + ist die `module_hub_git_url`.
>
> **Status:** Design abgestimmt (Brainstorming 2026-06-04, Till).

---

## Entscheidungen (abgestimmt)

| Frage | Entscheidung |
|---|---|
| Umfang v1 | **Solides Notizbuch**: Notiz = Titel + Markdown-Body; volles CRUD; pro User privat; Liste + Editor mit Markdown-Vorschau. |
| Heimat | **Hub-Repo `hydrahive2-modules`, design-rein** (eigenes Repo, Core bleibt sauber). Entwickelt im Hub-Klon, getestet per Install auf `.23` + Browser. |
| Per-User | Strikt: jede Notiz gehört dem anlegenden User (`require_auth`); fremde Notizen unsichtbar/unzugreifbar (kein IDOR). |
| Dienst | `has_service: false` (nur DB, kein externer Dienst). |
| Bewusst raus (YAGNI) | Listen/Checklisten (Einkaufszettel), Tags/Kategorien, Volltextsuche, Anhänge, Teilen/Mehrbenutzer-Notizen. Optional v2. |

---

## A. Heimat & Packaging

Neues Verzeichnis `notizbuch/` im Hub-Repo `hydrahive2-modules` (neben `example/`), Struktur nach dem Modul-Vertrag (`feature-map/28-modules.md`):
```
notizbuch/
  manifest.json          # id "notizbuch", name, icon, nav_group "working", has_service false, min_core_version
  backend/__init__.py     # def register(ctx): router + register_migrations("migrations")
  migrations/001_notizbuch.sql
  frontend/index.tsx      # export { routes, nav, i18n }
  frontend/NotizbuchPage.tsx
```
Plus Eintrag in `hub.json` des Hub-Repos: `{"id":"notizbuch","name":"Notizbuch","path":"notizbuch"}`.

`manifest.json`:
```json
{ "id": "notizbuch", "name": "Notizbuch", "version": "1.0.0", "icon": "NotebookPen",
  "nav_group": "working", "permissions": [], "has_service": false, "min_core_version": "2.0.0" }
```
(Icon = ein lucide-Name; der Core-`moduleIcon`-Resolver mappt String→Komponente, Fallback `Boxes`.)

Entwicklung: lokaler Klon von `hydrahive2-modules`, Modul dort bauen, pushen. Installation auf `.23` über den Modul-Knopf (zieht aus dem Hub).

## B. Datenmodell (pro User privat)

`migrations/001_notizbuch.sql`:
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
Per-Modul-Migration (eigene `module_schema_version`, vom Loader angewandt). Tabellenname `module_<id>_*`-Konvention. Daten bleiben bei Deinstall.

## C. Backend — CRUD, ownership-strikt

`backend/__init__.py`: `register(ctx)` registriert den Router + `register_migrations("migrations")`. Der User kommt aus `require_auth` (liefert `(username, role)` — der Username ist der Besitzer). Endpoints unter dem Framework-Prefix `/api/modules/notizbuch`:

| Methode | Pfad | Verhalten |
|---|---|---|
| `GET` | `/notes` | Liste der eigenen Notizen: `[{id, title, updated_at}]` (ohne body), `ORDER BY updated_at DESC`, `WHERE "user"=?` |
| `GET` | `/notes/{id}` | volle Notiz `{id,title,body,created_at,updated_at}`, **nur eigene** (sonst 404) |
| `POST` | `/notes` `{title, body}` | anlegen (user=auth), gibt die neue Notiz zurück |
| `PUT` | `/notes/{id}` `{title, body}` | ändern, **nur eigene** (sonst 404), setzt `updated_at` |
| `DELETE` | `/notes/{id}` | löschen, **nur eigene** (sonst 404) |

- Alle Queries strikt `WHERE "user" = ?` (Besitz-Filter) — fremde Notizen sind unsichtbar UND nicht per id zugreifbar (404 statt 403, kein Existenz-Leak).
- Eingabe-Validierung via Pydantic (`title`/`body` Strings; `title` darf leer sein, `body` darf leer sein — eine leere Notiz ist erlaubt, das Frontend führt). Fehlerbehandlung an der API-Grenze.
- `DB`-Zugriff über `from hydrahive.db.connection import db` (`with db() as c:`), parametrisiert (kein SQL-Injection).

## D. Frontend

- `frontend/index.tsx`: `routes = [{path:"/notizbuch", element:<NotizbuchPage/>}]`, `nav = [{path:"/notizbuch", icon:"NotebookPen", labelKey:"notizbuch", group:"working", roles:[]}]`, `i18n = {de:{notizbuch:{…}}, en:{notizbuch:{…}}}`.
- `NotizbuchPage.tsx`: zweispaltig — links Notiz-Liste (Titel + Datum, „neu"-Knopf), rechts Editor (Titel-Feld + Markdown-Textarea) mit **Vorschau-Umschalter/Live-Preview** + Speichern/Löschen. CRUD gegen die Endpoints via Core-`api`-Client (`@/shared/api-client`).
- **Nur vorhandene Core-Deps** (ein Modul kann keine neuen npm-Deps in den Core ziehen): `api`-Client, i18next, lucide, und die **vorhandene Markdown-Rendering-Komponente** des Cores (in der Plan-Phase ermittele ich, welche das ist — z.B. die im Team-Chat/Chat genutzte; sonst `react-markdown`, falls bereits Core-Dep). Das Modul-Frontend wird in den Core-Vite-Build kompiliert → Import aus `@/` ist erlaubt + erwünscht.
- Immutable State, sichtbare Fehleranzeige (kein stilles Schlucken).

## E. Datenfluss
Install (Hub→Kopie→Build→Restart→Loader→Migration→Router/Nav/Route) wie jedes Modul. Zur Laufzeit: `NotizbuchPage` → `GET /api/modules/notizbuch/notes` (require_auth → eigener User) → Liste; Auswahl → `GET /notes/{id}`; Speichern → `POST`/`PUT`; Löschen → `DELETE`. Server filtert immer auf den Auth-User.

## F. Fehlerbehandlung
- Fremde/nicht-existente Notiz → 404 (kein 403, kein Existenz-Leak).
- Leere Eingabe → erlaubt (leere Notiz); das Frontend kann eine leere unbenannte Notiz als „Unbenannt" anzeigen.
- Backend-Fehler → FastAPI-Standard-Fehlerformat; Frontend zeigt Fehler sichtbar.

## G. Verifikation (kein In-Repo-pytest — eigenes Repo)
1. Modul im Hub-Klon bauen, in `hydrahive2-modules` pushen (+ hub.json).
2. Auf `.23` über den Modul-Knopf installieren (zieht aus dem Hub) — Build + Restart + Migration laufen.
3. **Server-seitiger curl-Smoke** (controller): als User A anlegen/listen/ändern/löschen; **Zwei-User-Isolation** — User B sieht A's Notizen NICHT (`GET /notes` leer) und kann A's id NICHT lesen/ändern/löschen (404).
4. **Browser-E2E (Till):** „Notizbuch" im Nav → Notiz anlegen (Titel+Markdown) → Vorschau rendert → bearbeiten/löschen → nach Reload da. Deinstallieren → weg → **Re-Install → Notizen wieder da** (Daten-bleiben).

## H. Modul-Vertrag (Referenz, aus SP1)
- `register(ctx)`: `ctx.register_router(router)` + `ctx.register_migrations("migrations")`. Kein `register_service` (has_service false).
- Backend-IDs/Tabellen: `module_notizbuch_*`. Frontend-Exports: `{routes, nav, i18n}`. Loader + Codegen + Core-Hooks (App/Nav/i18n) sind bestehend (SP1) — das Modul liefert nur die Teile.

## In der Planungs-Phase zu klären (Detail, kein Blocker)
- Welche **Markdown-Komponente** der Core schon hat (Team-Chat/Chat nutzen Markdown) — die wiederverwenden; sonst `react-markdown` falls Core-Dep. (Verifizieren: `grep -rn "react-markdown\|Markdown" frontend/src`.)
- Genaues `require_auth`-Rückgabeformat (Username-Index) — gegen ein bestehendes auth-geschütztes Route bestätigen.
- Editor-Layout-Detail (Live-Preview vs. Tab-Umschalter) — UI-Feinheit.
- Hub-`hub.json`-Format (1 Eintrag, wie `example`).
