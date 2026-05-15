---
name: brainstorming
description: Design-first Workflow — erst vollständige Spezifikation, dann Code. Verhindert blinde Implementierung ohne klares Design.
when_to_use: Vor jeder neuen Feature-Implementierung, bei architektonischen Entscheidungen, wenn du "anfangen zu bauen" denkst ohne vollständiges Design
tools_required: [file_write, shell_exec]
---

# Brainstorming — Design First

## Harte Regel

**Kein Code ohne genehmigtes Design.** Wenn du planst Code zu schreiben, stoppe und führe erst diesen Prozess durch.

## 9-Schritt-Prozess

### Schritt 1: Problem definieren
Was genau soll gelöst werden? In 2-3 Sätzen, ohne Lösung zu erwähnen.

### Schritt 2: Bestehende Patterns prüfen
Gibt es ähnlichen Code in der Codebasis? Was kann wiederverwendet werden?

### Schritt 3: Constraints sammeln
- Technische Limits (Sprache, Framework, Performance)
- Geschäftliche Anforderungen
- Sicherheitsanforderungen
- Was explizit **nicht** gebaut werden soll

### Schritt 4: Optionen generieren
Mindestens 3 verschiedene Ansätze, kurz beschrieben (nicht ausimplementiert).

### Schritt 5: Trade-offs analysieren
Für jeden Ansatz: Vorteile, Nachteile, Risiken.

### Schritt 6: Empfehlung aussprechen
Welcher Ansatz, warum, mit welchen Trade-offs der User akzeptieren muss.

### Schritt 7: **Eine** Klärungsfrage stellen
Wenn noch etwas unklar ist — nur eine Frage pro Nachricht.

### Schritt 8: Spec schreiben
Nach Freigabe: Spec in `docs/specs/<feature>.md` ablegen.
Format: Was, Warum, Wie (grob), Akzeptanzkriterien.

### Schritt 9: Erst jetzt Code schreiben
Implementierung folgt der Spec, nicht umgekehrt.

## Red Flags — Stoppe wenn du denkst:

| Gedanke | Realität |
|---------|---------|
| "Ich fange einfach mal an" | Design zuerst, immer |
| "Das ist doch trivial" | Triviale Features zerstören Architekturen |
| "Ich kenne das Pattern" | Bestehende Patterns prüfen ist Pflicht |
| "Der User will das schnell" | Schlechtes Design kostet mehr Zeit |

## Ausgabe-Format

```markdown
## Problem
[1-3 Sätze]

## Optionen

### Option A: [Name]
- Vorteil: ...
- Nachteil: ...

### Option B: [Name]
- Vorteil: ...
- Nachteil: ...

### Option C: [Name]
- Vorteil: ...
- Nachteil: ...

## Empfehlung
Option [X], weil [Begründung].
Trade-off: [Was der User akzeptiert].

## Frage
[Eine klärende Frage, falls nötig]
```
