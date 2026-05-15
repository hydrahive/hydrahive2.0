---
name: writing-plans
description: Strukturierte Pläne vor dem Coden — atomare TDD-Tasks, keine TBD-Platzhalter, Implementierungsreihenfolge explizit.
when_to_use: Vor der Implementierung von Features mit >3 Dateien, bei Refactoring, bei neuen API-Endpoints, bei Datenbankmigrationen
tools_required: [file_write]
---

# Writing Plans

## Warum Pläne vor Code

Implementierung ohne Plan führt zu:
- Falsche Reihenfolge (Abhängigkeiten vergessen)
- Zu große Commits (alles auf einmal)
- Verlorene Übersicht bei Unterbrechungen
- Tests werden nachträglich hinzugefügt (zu spät)

## Plan-Format

```markdown
# Plan: [Feature-Name]

## Ziel
[Was wird nach diesem Plan existieren, das vorher nicht existierte]

## Dateien
- `pfad/zu/datei.py` — [was diese Datei tut]
- `pfad/zu/test_datei.py` — [was getestet wird]

## Implementierungsreihenfolge

### Task 1: [Name]
- [ ] Test schreiben: `test_xxx` in `tests/test_xxx.py`
- [ ] Test schlägt fehl (RED)
- [ ] Implementierung: [was genau]
- [ ] Test grün (GREEN)
- [ ] Commit: `test: ...` + `feat: ...`

### Task 2: [Name]
[gleiche Struktur]

## Akzeptanzkriterien
- [ ] [Was muss erfüllt sein damit fertig]
- [ ] [Zweites Kriterium]

## Nicht in diesem Plan
- [Was explizit ausgeschlossen wird]
```

## TDD-Struktur pro Task

Jeder Task folgt exakt diesem Ablauf:

1. **Test schreiben** — was soll die Funktion tun?
2. **Test ausführen** — er muss ROT sein (sonst testest du falsches)
3. **Minimalimplementierung** — nur genug um den Test grün zu machen
4. **Test ausführen** — er muss GRÜN sein
5. **Refactor** — code sauber machen ohne Tests zu brechen
6. **Commit** — test + implementation zusammen

## Verbotene Plan-Elemente

- "TBD" — wenn du es nicht weißt, kläre es jetzt
- "ähnlich wie X" ohne zu erklären was genau
- Tasks ohne klares Akzeptanzkriterium
- "Alles in einem großen Commit am Ende"

## Atomic Commits

Jeder Task = mindestens ein Commit. Format:
```
test: add test for [was]
feat: implement [was]
fix: handle edge case in [was]
```

Kein "WIP" Commit. Kein "fix stuff" Commit.

## Vor dem Plan schreiben

Fragen die beantwortet sein müssen:
1. Welche bestehenden Tests dürfen nicht brechen?
2. Gibt es Abhängigkeiten zwischen Tasks?
3. Welche Dateien werden angefasst?
4. Was ist der einfachste mögliche Weg?
