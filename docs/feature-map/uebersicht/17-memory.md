# Feature Map: Memory & Observations — Strukturiertes Agent-Gedächtnis

> **Modul:** `core/src/hydrahive/tools/_memory_*.py`  
> **Datenpfad:** `/var/lib/hydrahive2/agents/<agent-id>/memory.json`  
> **Was:** Strukturiertes Langzeitgedächtnis. Agent speichert gezielt Fakten, Präferenzen, Erkenntnisse.  
> **Warum:** Zwischen Sessions Infos behalten — Datamining ist Rohdaten, Memory ist kuratiertes Wissen.

---

## Unterschied Memory vs. Datamining

| Aspekt | Memory | Datamining |
|---|---|---|
| Art | Kuratiert, strukturiert | Rohe Session-Daten |
| Wer schreibt | Agent selbst (explizit) | Automatisch (alle Events) |
| Format | Key/Value + Metadata | Events/Messages |
| Zugriff | `read_memory`, `write_memory`, `search_memory` | `datamining_*` Tools |
| Scope | Pro Agent | Global (alle Agents) |
| Confidence | Ja (0.0–1.0) | Nein |
| Expiry | Ja (TTL) | Nein (permanent) |

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `tools/_memory_model.py` | Pydantic-Modell: `MemoryEntry` (key, content, confidence, expires_at, project, superseded_by) |
| `tools/_memory_store.py` | CRUD für Memory-Einträge. JSON-Persistenz pro Agent. |
| `tools/_memory_io.py` | Lese-/Schreib-Hilfsfunktionen (Filter, Sortierung) |
| `tools/read_memory.py` | Tool: Memory lesen |
| `tools/write_memory.py` | Tool: Memory schreiben/löschen |
| `tools/search_memory.py` | Tool: Memory durchsuchen |

---

## Memory-Eintrag-Format

```json
{
  "key": "hydra-emoji-prompt-template",
  "content": "## Hydra Emoji Prompt-Template\n\n...",
  "confidence": 0.99,
  "project": "hydrahive2",
  "created_at": "2026-06-02T10:00:00",
  "updated_at": "2026-06-02T11:00:00",
  "expires_at": null,
  "superseded_by": null,
  "access_count": 5
}
```

---

## Confidence-System

```python
write_memory(key="...", content="...", confidence=0.5)  # neu, unsicher
write_memory(key="...", content="...", confidence=0.9)  # gut bestätigt
```

- Beim wiederholten Schreiben auf denselben Key: Confidence wird erhöht (Reinforcement)
- Ähnliche Einträge werden automatisch als "superseded" markiert (Contradiction Detection)
- `search_memory(min_confidence=0.7)` filtert unsichere Einträge heraus

---

## TTL / Ablauf

```python
write_memory(key="...", expires_at="+2h")    # läuft in 2h ab
write_memory(key="...", expires_at="+1d")    # läuft morgen ab
write_memory(key="...", expires_at="+7d")    # läuft in einer Woche ab
write_memory(key="...", expires_at="+4w")    # läuft in 4 Wochen ab
write_memory(key="...", expires_at="2026-12-31T23:59:00")  # fixer Timestamp
```

---

## Projekt-Scoping

```python
write_memory(key="...", project="hydrahive2")  # nur in hydrahive2-Projekt sichtbar
write_memory(key="...")                         # global (in allen Projekten sichtbar)

read_memory()  # listet: aktives Projekt + globale Einträge
read_memory(project="*")  # listet: alle Projekte
```

---

## Observations

Neben Memory gibt es **Observations** — Langzeit-Beobachtungen:
- Gespeichert in `/var/lib/hydrahive2/agents/<agent-id>/observations/`
- Format: Markdown-Dateien
- Weniger strukturiert als Memory
- Mehr wie ein Notizbuch des Agents

```python
# intern in tools/_observations.py
save_observation(agent_id, topic, content)
list_observations(agent_id)
```

---

## Memory-Persistenz

```
/var/lib/hydrahive2/agents/<agent-id>/memory.json
{
  "entries": [
    {
      "key": "user-prefers-dark-theme",
      "content": "Till mag Dark Mode und bevorzugt ...",
      "confidence": 0.95,
      "project": null,
      ...
    }
  ]
}
```

---

## Nutzungs-Pattern

```python
# Typischer Memory-Workflow:
read_memory()          # Was weiß ich schon?
# → Prüfen ob relevante Keys existieren

write_memory(
    key="project-status-hydrahive2",
    content="Emojis fertig (159). Nächste: feature-map.",
    project="hydrahive2",
    confidence=0.9
)

search_memory("emoji")  # Semantic suchen
```

---

## Verwandte Subsysteme

- **→ Tools** (`02-tools.md`): `read/write/search_memory` als Tools
- **→ Datamining** (`16-datamining.md`): komplementäres Rohdaten-Gedächtnis
- **→ Agents** (`05-agents.md`): Memory ist pro Agent gespeichert
