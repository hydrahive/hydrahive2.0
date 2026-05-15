---
name: using-superpowers
description: Erklärt das Skill-System und wann Skills genutzt werden müssen
when_to_use: Wenn du verstehen willst wie das Skill-System funktioniert oder wann du Skills nutzen sollst
tools_required: [list_skills, load_skill]
---

# Skills — Wie und wann nutzen

## Grundregel

Wenn auch nur **1% Chance** besteht dass ein Skill für die aktuelle Aufgabe passt: **lade ihn zuerst**.

Skills sind keine optionalen Tipps — sie sind Arbeitsanweisungen die Till und das Team hinterlegt haben. Einen passenden Skill zu ignorieren ist ein Fehler.

## Workflow

1. **Aufgabe erhalten** → zuerst: passt ein Skill?
2. Skill-Tabelle im System-Prompt prüfen (immer sichtbar)
3. Passt einer? → `load_skill(name)` aufrufen
4. Skill lesen, **dann** mit der Aufgabe beginnen
5. Unsicher welcher Skill passt? → `list_skills` aufrufen für Details

## Wann welcher Skill?

| Situation | Skill |
|-----------|-------|
| Bug finden / etwas funktioniert nicht | `debugging` |
| Code schreiben oder ändern | `code-review` (danach) |
| Tests schreiben | `test` |
| Refactoring | `refactor` |
| Dokumentation | `docs` |
| Git commit / PR | `git-workflow` |
| HydraHive2-spezifischer Code | `hh-review` |
| Skill-Übersicht | `skill-catalog` |

## Red Flags — diese Gedanken sind falsch

| Gedanke | Warum falsch |
|---------|-------------|
| "Das ist eine einfache Aufgabe" | Einfache Aufgaben haben oft passende Skills |
| "Ich brauche erst mehr Kontext" | Skill-Check kommt VOR dem Kontext sammeln |
| "Ich kenne das Thema" | Skills können neuere Regeln enthalten als dein Training |
| "Der Skill ist zu spezifisch" | Spezifisch = genau richtig für die Situation |

## Skill-Priorität

1. **Prozess-Skills zuerst** (debugging, test) — definieren WIE du vorgehst
2. **Umsetzungs-Skills danach** (hh-review, code-review) — definieren WAS du prüfst
