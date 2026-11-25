---
name: using-superpowers
description: Erklärt das Skill-System und wann Skills genutzt werden müssen
when_to_use: Wenn du verstehen willst wie das Skill-System funktioniert oder wann du Skills nutzen sollst
tools_required: [list_skills, load_skill]
---

# Skills — Wie und wann nutzen

> Die Arbeitsablauf-Skills (brainstorming, writing-plans, debugging, verification, …) folgen Superpowers v7.0.2 (github.com/obra/superpowers, MIT, © 2025 Jesse Vincent – Lizenztext: docs/third-party/superpowers-LICENSE).

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
| Neue Idee, Funktion mit offenen Punkten, „lass uns überlegen“ | `brainstorming` |
| Spec/Design steht, mehrteilige Umsetzung | `writing-plans` |
| Aufgabe an Agenten geben, Teilprobleme parallel | `dispatching-parallel-agents` |
| Bug finden / etwas funktioniert nicht | `debugging` |
| Tests schreiben | `test` |
| Review durchführen oder anfordern | `code-review` |
| Review-Befunde sind da | `receiving-code-review` |
| Bevor du „fertig“, „grün“, „läuft“ sagst | `verification-before-completion` |
| Branch fertig, Merge, Worktree aufräumen | `finishing-development-branch` |
| Refactoring | `refactor` |
| Dokumentation | `docs` |
| Git commit / PR | `git-workflow` |
| HydraHive2-spezifischer Code | `hh-review` |
| Skill-Übersicht | `skill-catalog` |

Typische Reihenfolge bei neuer Arbeit: `brainstorming` → `writing-plans` → umsetzen (selbst oder `dispatching-parallel-agents`) → `code-review` → `receiving-code-review` → `verification-before-completion` → `finishing-development-branch`.

## Red Flags — diese Gedanken sind falsch

| Gedanke | Warum falsch |
|---------|-------------|
| "Das ist eine einfache Aufgabe" | Einfache Aufgaben haben oft passende Skills |
| "Ich brauche erst mehr Kontext" | Skill-Check kommt VOR dem Kontext sammeln |
| "Ich kenne das Thema" | Skills können neuere Regeln enthalten als dein Training |
| "Der Skill ist zu spezifisch" | Spezifisch = genau richtig für die Situation |

## Skill-Priorität

1. **Prozess-Skills zuerst** (brainstorming, writing-plans, debugging, test) — definieren WIE du vorgehst
2. **Umsetzungs-Skills danach** (hh-review, code-review) — definieren WAS du prüfst
