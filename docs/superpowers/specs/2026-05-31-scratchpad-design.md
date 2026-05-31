# Design: Scratchpad — globale Mensch→Agent-Ideenfläche

**Datum:** 2026-05-31
**Status:** Design abgestimmt (Brainstorming mit Till). Noch NICHT in SPEC.md, noch nicht gebaut.
**Vorgeschichte:** Till hatte in HydraHive 1 ein Scratchpad (`octopos/.../scratchpad_service.py` — „Free whiteboard for ideas"). Dort: pro Agent, flüchtig (bei Session geleert), reines Markdown, Auto-Injection in den Agent-Kontext. HH2 baut das Konzept neu mit anderem Scope und cache-sicherer Anbindung.

---

## Zweck

Ein Ort, an dem Till **Ideen notiert und veranschaulicht**, die sein Buddy/Masteragent **auslesen** kann. Eine bewusste Mensch→Agent-Übergabefläche für unstrukturierte Gedanken — kein Memory (das ist Auto-Gedächtnis aus Sessions), sondern bewusster Input.

## Scope-Entscheidungen (mit Till abgestimmt)

| Frage | Entscheidung |
|---|---|
| Bezugsrahmen | **Global** — ein Scratchpad pro User (Till + sein Buddy/Master), nicht projektgebunden |
| Lebensdauer | **Persistent** über Sessions, einzelne Punkte als erledigt abhakbar |
| Format | **Markdown + Mermaid** (Mermaid v1 als Code-Block, Rendering erst v1.1) |
| Lese-Modus | **Hybrid** — statischer Prompt-Hinweis + `read_scratchpad`-Tool on-demand |
| Agent-Schreibrecht | **Ja**, aber in **getrennter Zone** (Agent kann Tills Text technisch nicht anfassen) |
| Frontend | Eigener globaler Menüpunkt „Scratchpad" |

## Architektur

### Trennung über zwei Dateien (Datenschutz)
Statt einer Datei mit Marker (verrutschbar) → **zwei physisch getrennte Dateien** pro User:

```
settings.data_dir/scratchpad/<user_id>/user.md     ← nur Till schreibt (UI)
settings.data_dir/scratchpad/<user_id>/agent.md    ← nur der Agent schreibt (Tool)
```

Harte Trennung auf FS-Ebene: `write_scratchpad` (Agent) erreicht `user.md` technisch nicht. `user_id` kommt server-seitig aus dem Auth-Token → kein Path-Traversal, keine fremden Scratchpads.

### Datenfluss

```
Till (Browser) ──PUT user.md──►  user.md   ──┐
                                              ├──read_scratchpad──► Buddy/Master
Buddy/Master ──write_scratchpad──► agent.md ──┘   (beide Zonen, klar beschriftet)
                ▲ kann user.md NICHT schreiben
```

### Backend (kleine, fokussierte Module — CLAUDE.md ~200 Zeilen/Datei)

**`core/src/hydrahive/scratchpad/service.py`**
- `get_user(user_id) -> str`, `save_user(user_id, content)` → `user.md`
- `get_agent(user_id) -> str`, `save_agent(user_id, content)` → `agent.md`
- `clear_agent(user_id)` (Till darf die Agent-Zone leeren)
- `get_combined(user_id) -> str` → beide Zonen mit Überschriften (für `read_scratchpad`)
- Atomic write (temp + `os.replace`), konsistent mit HH2-Konvention (vgl. S3-Fix, `_observations`)
- Größenlimit pro Zone (z.B. 256 KB) → fail mit klarer Meldung

**`core/src/hydrahive/api/routes/scratchpad.py`** (`require_auth`, user aus Token)
- `GET /api/scratchpad` → `{ user_content, agent_content }`
- `PUT /api/scratchpad` → `{ content }` setzt **nur** `user.md`
- `DELETE /api/scratchpad/agent` → leert die Agent-Zone

**`core/src/hydrahive/tools/read_scratchpad.py`** (Core-Tool, `Tool(...)`-Pattern)
- Args: keine. Gibt `get_combined()` als Text zurück — Agent sieht offene/erledigte Punkte an `[ ]`/`[x]` und Mermaid als Code. Null Parsing, null Multimodal.

**`core/src/hydrahive/tools/write_scratchpad.py`** (Core-Tool)
- Args: `content` (string). Ersetzt **nur** `agent.md` (`save_agent`). Kann `user.md` nicht berühren.
- Erst-lesen-Konvention im Prompt: Agent ruft i.d.R. `read_scratchpad` davor, um die Agent-Zone nicht versehentlich zu leeren.

### Hybrid-Anbindung (cache-sicher)
- **Statischer** Satz im Master/Buddy-Prompt im `stable_system`-Block: „Es gibt ein Scratchpad mit Tills Ideen. Lies es mit `read_scratchpad`, wenn relevant. Eigene Notizen schreibst du mit `write_scratchpad` — nur in deinen Bereich, Tills Bereich ist tabu." Ändert sich nie → **bricht den Prompt-Cache nicht** (vgl. `feedback_anthropic_cache_semantics`).
- **Volatiler Inhalt** kommt nur als Tool-Result in den `messages`-Block, wenn der Agent das Tool ruft — nie in den `system`-Block.

### Frontend

**`frontend/src/features/scratchpad/ScratchpadView.tsx`** — globaler Menüpunkt „Scratchpad". Zwei Bereiche:
- **„Meine Ideen"** — Editor (Textarea) + Live-Preview, debounced Auto-Save via `PUT`.
- **„Agent-Notizen"** — read-only Preview + „Leeren"-Button (`DELETE`).
- **`frontend/src/features/scratchpad/api.ts`** — `getScratchpad()`, `saveScratchpad(content)`, `clearAgentNotes()`.

**Rendering:** bestehende `features/chat/Markdown.tsx` wiederverwenden (DRY). `remark-gfm` rendert `- [ ]` bereits als klickbare Checkboxen; Klick togglet die Zeile in der Quelle + speichert. Mermaid erscheint in v1 als Code-Block (kein neues Paket). `Markdown.tsx` bleibt unverändert.

## Sicherheit
- Auth-gebunden pro User (`user_id` aus Token, nie aus Request).
- Größenlimit pro Zone.
- Agent kann `user.md` technisch nicht schreiben (FS-Trennung).
- Atomic write gegen Korruption bei gleichzeitigem Mensch/Agent-Zugriff (last-write-wins akzeptabel für Single-User-Fläche).

## Tests
- **`service.py`**: user/agent getrennt get/save, `clear_agent`, `get_combined`-Format, Größenlimit, atomic write. **Kern-Guard:** nach `save_agent` ist `user.md` byte-identisch unverändert (Tills Datenschutz).
- **API**: auth required, PUT-Roundtrip setzt nur user_content, DELETE leert nur agent.
- **Tools**: `read_scratchpad` liefert beide Zonen; `write_scratchpad` berührt **nur** `agent.md` (Regression-Guard gegen user.md-Mutation).
- **Frontend**: `tsc -b` grün (NICHT `tsc --noEmit` — toter Wächter, siehe `feedback_frontend_tsc_check`).

## Nicht-Ziele (v1)
- Mermaid-Rendering im Browser → v1.1.
- Bilder/Foto-Upload / echtes Zeichen-Whiteboard (multimodal-abhängig).
- Pro-Projekt- oder Pro-Agent-Scratchpads (nur global v1).
- Versionierung/History der Scratchpad-Inhalte.

## Offene Schritte vor dem Bau
1. **SPEC.md-Ergänzung** (CLAUDE.md Regel 4 + 8): Scratchpad als neue Core-Komponente in SPEC.md aufnehmen — als **Vorschlag mit Diff**, auf Tills explizites OK warten, dann **Standalone-Commit** (nur SPEC.md).
2. Danach: `writing-plans`-Skill → Implementierungsplan.
