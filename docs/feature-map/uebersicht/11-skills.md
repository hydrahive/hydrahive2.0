# Feature Map: Skills — Markdown-Prompt-Templates

> **Modul:** `core/src/hydrahive/skills/`  
> **Datenpfad:** `/var/lib/hydrahive2/skills/system/`  
> **Was:** Wiederverwendbare Anweisungs-Templates. Agent lädt sie on-demand in den Kontext.  
> **Warum:** Statt langen System-Prompts: modulare Spezial-Wissen-Blöcke die nur geladen werden wenn gebraucht.

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `skills/loader.py` | `list_for_agent()` — lädt aktive Skills für einen Agent. `load_skill(name)` — Skill-Body. |

---

## Skill-Dateiformat

Jeder Skill ist eine Markdown-Datei:
```
/var/lib/hydrahive2/skills/system/<skill-name>.md
```

### Frontmatter (YAML)
```yaml
---
name: brainstorming
description: "Strukturiertes Brainstorming vor Feature-Implementierungen"
when_to_use: "Vor jeder neuen Feature-Implementierung, bei architektonischen Entscheidungen"
category: development
---
```

### Body
Der Markdown-Body ist der eigentliche Skill-Inhalt — wird als System-Prompt-Block injiziert.

---

## Alle System-Skills

| Skill | Wann nutzen |
|---|---|
| `brainstorming` | Vor Feature-Impl., bei Architektur-Entscheidungen |
| `code-review` | Bei Code-Review oder Bug-Suche |
| `debugging` | Wenn Bug gefunden werden soll |
| `dispatching-parallel-agents` | Wenn ≥2 unabhängige Teilprobleme |
| `docs` | Dokumentation schreiben/verbessern |
| `finishing-development-branch` | Wenn Feature-Branch fertig sein könnte |
| `generate-music` | Musik generieren |
| `generate-speech` | TTS / Voiceover |
| `git-workflow` | Code ändern + committen |
| `hh-review` | Vor Commit auf HH2-Code (Architektur-Prüfung) |
| `medical-akte` | Medizinische Infos in Akte schreiben/abfragen |
| `medical-research` | Medizinische Recherche mit Quellen |
| `performance-profile` | Sessions optimieren, Cache-Misses |
| `project-management` | Issues, PRs, Milestones |
| `refactor` | Code refactoren |
| `security-audit` | Security-Check neuer Endpoints/Tools |
| `skill-catalog` | Welche Skills gibt es? |
| `test` | Tests schreiben |
| `using-superpowers` | Wie funktioniert das Skill-System? |
| `verification-before-completion` | Vor jeder "fertig"-Meldung |
| `writing-plans` | Vor Implementierung >3 Dateien |

---

## Wie Skills in den Kontext kommen

### Weg 1: Automatisch via Agent-Config
```json
{
  "skills": ["git-workflow", "brainstorming"]
}
```
Diese Skills werden bei JEDEM Run dieses Agents in den System-Prompt geladen.

### Weg 2: On-Demand via `load_skill`-Tool
```
Agent: "Ich lade jetzt den brainstorming-Skill..."
[load_skill("brainstorming")]
→ Skill-Body wird als Kontext-Block in die aktuelle Session injiziert
```

### Weg 3: Via `list_skills` + `load_skill` 
Der Agent nutzt `list_skills` um zu sehen was verfügbar ist,
dann `load_skill` um den Body zu laden.

---

## System-Prompt-Aufbau mit Skills

```
[Stable Block]
  Du bist Seven of Nine...

[Soul Block] (wenn vorhanden)
  Langzeit-Charakter-Beschreibung...

[Skill-Blöcke] (geladene Skills)
  ## git-workflow
  Wenn du Code änderst, folge diesem Workflow...
  
  ## brainstorming
  Vor jeder Implementierung...

[Volatile Block]
  Aktuelles Datum: 2026-06-02
  Aktive Projekte: ...

[Summary Block] (wenn Compaction vorhanden)
  Zusammenfassung früherer Konversation: ...
```

---

## Verwandte Subsysteme

- **→ Runner** (`01-runner.md`): `system_prompt.compose()` integriert Skills
- **→ Agents** (`05-agents.md`): `skills`-Liste in Agent-Config
- **→ API** (`04-api.md`): `routes/skills.py` — CRUD-Endpoints
- **→ Tools** (`02-tools.md`): `list_skills`, `load_skill` sind Tools
