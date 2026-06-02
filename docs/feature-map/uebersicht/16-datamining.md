# Feature Map: Datamining — Langzeitgedächtnis & Analytics

> **Modul:** `core/src/hydrahive/db/mirror*.py` + `mcp-servers/datamining/`  
> **Frontend:** `frontend/src/features/datamining/`  
> **Was:** Alle Session-Daten durchsuchbar machen. Timeline, Semantic Search, Graph-Visualisierung.  
> **Warum:** Agent-Gedächtnis über Session-Grenzen hinaus. "Was haben wir letzte Woche besprochen?"

---

## Architektur

```
SQLite (Haupt-DB)
    │ Mirror-Sync
    ▼
PostgreSQL Mirror (optional)
    ├── Events-Tabelle (Messages, Tool-Calls, ...)
    ├── Embeddings (für Semantic Search)
    └── Graph (Agents, Sessions als Knoten/Kanten)
```

Ohne PostgreSQL: Nur SQLite-basierte Suche (eingeschränkt).
Mit PostgreSQL: Volltextsuche, Embedding-Search, Graph-Visualisierung.

---

## Backend-Dateien

| Datei | Verantwortung |
|---|---|
| `db/mirror.py` | Mirror-Hauptmodul, Sync-Koordination |
| `db/mirror_query.py` | **Query-Layer**: `search()`, `semantic()`, `timeline()`, `today()` |
| `db/_mirror_ddl.py` | PostgreSQL-DDL: CREATE TABLE, Indizes |
| `db/_mirror_writes.py` | Write-Ops in Mirror |
| `db/_mirror_sessions.py` | Session-Sync |
| `db/_mirror_embed.py` | Embedding-Generierung (Sentence-Transformers) |
| `db/_mirror_search.py` | Volltext-Suche + Vektor-Suche |
| `db/_mirror_explode.py` | JSON-Content in suchbare Felder explodieren |
| `db/mirror_graph.py` | Graph: Knoten + Kanten aufbauen |
| `db/mirror_graph_topology.py` | Graph-Algorithmen |
| `db/mirror_import_*.py` | Import-Module für Git, JSONL, Logs, Shell, SQLite |
| `hooks/datamining-sync/` | Background-Hook für automatischen Sync |

---

## Datamining-Tools (Agent-Tools)

| Tool | Query-Typ | Beschreibung |
|---|---|---|
| `datamining_search` | Volltext | Sucht Strings in allen Events. `from_date`, `agent_name`, `event_type` filter |
| `datamining_semantic` | Semantic | Ähnlichkeitssuche per Embeddings. "Was haben wir über X besprochen?" |
| `datamining_timeline` | Zeitstrahl | Alle Sessions gruppiert nach Tag. `from_date`/`to_date`, `sort_by` |
| `datamining_today` | Heute | Was ist heute passiert? Sessions, Requests, Tool-Calls |

---

## Event-Typen im Mirror

| event_type | Beschreibung |
|---|---|
| `user_input` | User-Nachrichten |
| `assistant_text` | Agent-Antworten |
| `tool_call` | Tool-Aufrufe (Name + Args) |
| `tool_result` | Tool-Ergebnisse |
| `compaction` | Compaction-Summaries |
| `thinking` | Reasoning-Blöcke (wenn Extended Thinking) |

---

## Timeline-Format

```python
datamining_timeline(from_date="2026-05-01", to_date="2026-06-02")
→ {
    "days": [
        {
            "date": "2026-06-02",
            "session_count": 3,
            "total_events": 142,
            "agents": ["Seven of Nine", "ISBN Extractor"]
        },
        ...
    ]
}
```

---

## Frontend-Tabs

| Tab | Datei | Inhalt |
|---|---|---|
| Sessions | `SessionsTab.tsx` | Session-Liste mit Filter/Suche |
| Live Feed | `LiveFeedTab.tsx` | Echtzeit-Events-Stream |
| Search | `SearchTab.tsx` | Volltext + Semantic Suche |
| Stats | `StatsTab.tsx` | Token-Verbrauch, Kosten, Aktivität |
| Graph | `GraphTab.tsx` | Visualisierung Agent/Session-Graph |

---

## Import-Funktionen

Externe Daten können in den Mirror importiert werden:

```python
# Git-Commits importieren:
mirror_import_git.import_repo("/opt/hydrahive2")

# JSONL importieren (z.B. Claude-Chat-Export):
mirror_import_jsonl.import_file("conversations.jsonl")

# Shell-Output importieren:
mirror_import_shell.import_output("ls -la", output="...")
```

---

## Issue-Import

Datamining kann GitHub/GitLab Issues importieren:
```
POST /api/datamining/transfer {type: "github_issues", repo: "..."}
→ Issues landen als Events im Mirror
→ Durchsuchbar wie normale Events
```

---

## Verwandte Subsysteme

- **→ DB** (`03-db.md`): Mirror ist Teil der DB-Schicht
- **→ Tools** (`02-tools.md`): `datamining_*` Tools
- **→ Memory** (`17-memory.md`): Memory ist komplementär (strukturiert vs. Rohdaten)
