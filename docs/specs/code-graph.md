# Code-Graph — Projekt-Codebase als navigierbarer Wissensgraph (Etappe 1)

## Was
Jedes Projekt bekommt einen **Code-Graph**: ein Button „Graph" in der Projekt-
Aktionsleiste öffnet ein Overlay, in dem man ausgewählte Code-Verzeichnisse zu
einem interaktiven Abhängigkeitsgraphen verarbeitet (God-Nodes, Communities,
Import-Zyklen, Refactoring-Hinweise). Man wählt die zu scannenden Verzeichnisse,
baut den Graphen und schaut sich die interaktive `graph.html` + den Report an.

## Warum
Agenten (und Menschen) verstehen eine Codebase schneller über einen Graphen als
durch ständiges Grep-und-Lesen. Etappe 1 liefert den sichtbaren Nutzen (bauen +
anschauen). Agenten-Tools (query/explain/path) folgen in Etappe 2.

## Scope Etappe 1
- **Nur Code, 100 % lokal, 0 API-Kosten, kein Datenabfluss.** (Doku/Bilder-
  Graphing wäre LLM-basiert → späterer optionaler Schalter.)
- **Ein Graph pro Projekt** (nicht global). Wählbare Scan-Verzeichnisse.

## Bestehende Muster (wiederverwendet)
- Underlying: **graphify** (`graphifyy` auf PyPI), `graphify update <dir>` baut
  rein lokal per tree-sitter-AST (kein LLM). Erzeugt `graphify-out/graph.json`,
  `graph.html`, `GRAPH_REPORT.md`.
- Overlay-Muster wie `ProjectGitOverlay` / `ProjectInsightsOverlay`.
- Button in `ProjectActionGroups` (neben Git/Integrationen).
- Datei-Auslieferung über `/api/files` (graph.html liegt unter data_dir/workspaces).

## Wie
### Isoliertes venv (on-demand, Option B)
- graphify **nicht** in die Kern-Dependencies. Stattdessen ein eigenes venv unter
  `settings.data_dir / "tools" / "graphify" / "venv"`, das beim ersten Build
  automatisch per `python -m venv` + `pip install graphifyy` angelegt wird.
- `code_graph.py` ruft `<venv>/bin/graphify update <dir>` als subprocess.
- Bootstrap-Status abfragbar (installiert ja/nein), damit die UF „wird
  eingerichtet…" zeigen kann.

### Datenablage (pro Projekt)
- Config: `<workspace>/.graphify/config.json` → `{ scan_dirs: [rel...], updated_at }`.
- Graph-Output: `<workspace>/.graphify/out/` (graph.json, graph.html, GRAPH_REPORT.md).
- Default-Scan-Dirs: automatisch aus vorhandenen Repos/`src`-Ordnern vorgeschlagen
  (z.B. `<repo>/src`, `<repo>/frontend/src`), sonst leer.

### Backend `code_graph.py` (Modul) + Route
- `bootstrap_status()` → `{ installed: bool }`.
- `ensure_installed()` → legt venv an + pip install (idempotent, mit Timeout).
- `get_config(project_id)` / `set_config(project_id, scan_dirs)` — scan_dirs gegen
  Path-Traversal validiert (müssen **innerhalb** des Workspace liegen, existieren).
- `build(project_id)` → für jedes scan_dir `graphify update`; danach die Outputs
  ins gemeinsame `.graphify/out/` konsolidieren; liefert Kurz-Metriken
  (nodes/edges/communities) + Report-Auszug (God-Nodes, Zyklen).
- `status(project_id)` → letzter Build (Zeit, Metriken, ob graph.html existiert).
- Routen (neuer Router `code_graph.py`, require_auth + _authorize):
  - `GET  /api/projects/{id}/code-graph/status`
  - `GET/PUT /api/projects/{id}/code-graph/config`
  - `POST /api/projects/{id}/code-graph/build`
  - Report/HTML über `status` (Pfade) → Frontend lädt via `/api/files`.

### Frontend
- `projectsApi`-Erweiterung bzw. `codeGraphApi` (status/config/build).
- **`ProjectGraphOverlay`**: Verzeichnis-Auswahl (Checkbox-Liste aus Vorschlägen +
  manuell), „Graph bauen" (zeigt Fortschritt), nach Build: Metriken + God-Nodes +
  Zyklen aus dem Report, und die interaktive `graph.html` als iframe
  (`/api/files?path=…`). Bootstrap-Hinweis, falls venv erst eingerichtet wird.
- **Button „Graph"** in `ProjectActionGroups`, verdrahtet in `ProjectCockpitPage`.

## Akzeptanzkriterien
- [ ] „Graph"-Button öffnet Overlay; man kann Scan-Verzeichnisse wählen (persistiert).
- [ ] „Graph bauen" erzeugt lokal (ohne LLM) den Graphen; Fortschritt sichtbar.
- [ ] Interaktive graph.html + God-Nodes/Zyklen/Metriken werden angezeigt.
- [ ] scan_dirs sind gegen Path-Traversal geschützt (nur innerhalb Workspace).
- [ ] venv wird on-demand gebootstrappt; Kern-Dependencies unverändert.
- [ ] Backend-Tests grün (config round-trip, dir-validation); Build/Typecheck/ESLint grün.

## Etappe 2 (später, nicht dieser PR)
Agenten-Tools `graph_query` / `graph_explain` / `graph_path` / `graph_affected`
(dünne Wrapper über `graphify query/explain/path/affected` auf `graph.json`) +
Skill „code-graph" (wann Graph statt Grep). Optional MCP-Server. Optional
Doku-Graphing (LLM).
