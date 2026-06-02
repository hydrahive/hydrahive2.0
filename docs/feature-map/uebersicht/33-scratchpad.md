# Feature Map: Scratchpad — User-Notizen & Agent-Zone

> **Modul:** `core/src/hydrahive/scratchpad/`  
> **Frontend:** `frontend/src/features/scratchpad/`  
> **Was:** Freitext-Notizbuch. User schreibt eigene Notizen. Agent hat eigene geschützte Zone.  
> **Warum:** Persistentes Notizbuch — zwischen Sessions erhalten. Agent-Notizen ≠ User-Notizen.

---

## Zwei-Zonen-Modell

```markdown
# Till's Notizen
[Dieser Bereich gehört dem User — TABU für Agents]

Ideen für nächste Woche:
- Mehr Kaffee
- HH2 Datamining UI verbessern

---

# Agent-Notizen
[Dieser Bereich gehört dem Agent — User liest nur]

## Laufende Aufgaben (Seven of Nine)
- Feature-Map-Dokumentation: 32/35 fertig
- Emojis: 159 generiert und eingebunden
```

---

## Regeln

1. **User-Zone:** Alles vor `# Agent-Notizen` (oder einem definierten Separator)
2. **Agent-Zone:** Nur der Agent darf hier schreiben (via `write_scratchpad`)
3. **Agent darf nie User-Zone überschreiben** — `write_scratchpad` ersetzt nur die Agent-Zone
4. Vor jedem `write_scratchpad`: `read_scratchpad` lesen um bestehende Agent-Notizen nicht zu verlieren

---

## Tools

```python
# Lesen — ganzer Scratchpad (User + Agent)
read_scratchpad()
→ {user_content: "...", agent_content: "...", full: "..."}

# Schreiben — NUR Agent-Zone
write_scratchpad(content="## Meine Notizen\n\n...")
→ Ersetzt Agent-Zone komplett
```

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `scratchpad/store.py` | Lesen/Schreiben des Scratchpads. Zonen-Trennung. |
| `scratchpad/zones.py` | Zonen-Parser (User-Zone vs. Agent-Zone) |
| `tools/read_scratchpad.py` | Tool: Scratchpad lesen |
| `tools/write_scratchpad.py` | Tool: Agent-Zone schreiben |
| `api/routes/scratchpad.py` | REST-Endpoints |
| `frontend/features/scratchpad/ScratchpadPage.tsx` | Editor-UI (Split-Ansicht) |
| `frontend/features/scratchpad/ScratchpadEditor.tsx` | Markdown-Editor für User-Zone |

---

## Persistenz

```
/var/lib/hydrahive2/users/<user-id>/scratchpad.md
```

Pro User ein Scratchpad. Keine Versionierung (kein Git).

---

## Frontend

`ScratchpadPage.tsx` zeigt:
- Links: Markdown-Editor für User-Zone (live preview)
- Rechts: Agent-Zone (read-only, Markdown-gerendert)

---

## Verwandte Subsysteme

- **→ Memory** (`17-memory.md`): Memory ist strukturiert, Scratchpad ist Freitext
- **→ Buddy** (`09-buddy.md`): Buddy liest Scratchpad um User-Kontext zu haben
