---
name: skill-catalog
description: Listet alle verfügbaren Skills mit Name, Beschreibung und Anwendungsfall. Nutze diesen Skill wenn du einen Überblick über verfügbare Skills brauchst oder den richtigen Skill für eine Aufgabe finden willst.
when_to_use: Wenn der User fragt welche Skills verfügbar sind, oder wenn du dir nicht sicher bist welcher Skill für eine Aufgabe passt.
tools_required: [list_skills]
---

# Skill-Katalog

Rufe `list_skills` auf und gib eine übersichtliche Markdown-Tabelle aller verfügbaren Skills aus.

Format:

```
## Verfügbare Skills

| Skill | Beschreibung | Wann nutzen |
|-------|-------------|-------------|
| `code-review` | ... | ... |
| `debug` | ... | ... |
```

Danach: frage den User welchen Skill er nutzen möchte und lade ihn mit `load_skill`.
