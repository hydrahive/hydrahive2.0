---
name: finishing-development-branch
description: Strukturierter Abschluss eines Development-Branches — Tests zuerst, dann Entscheidung (merge/PR/keep/discard), dann Cleanup.
when_to_use: Wenn ein Feature-Branch fertig sein könnte, vor jedem Merge, wenn du "das kann ich jetzt mergen" denkst
tools_required: [shell_exec]
---

# Finishing a Development Branch

## Reihenfolge ist Pflicht

Cleanup **nach** Merge, nicht vorher. Entscheidung **nach** Tests, nicht davor.

## Schritt 1: Tests verifizieren

```bash
# Alle Tests grün?
pytest -v

# Nur neue Tests für diesen Branch
git diff main..HEAD --name-only | grep test | xargs pytest -v

# Keine Regression in bestehenden Tests
pytest --tb=short
```

**Stoppe hier wenn Tests rot sind.** Erst fixen, dann weiter.

## Schritt 2: Branch-Status prüfen

```bash
# Commits die noch nicht in main sind
git log main..HEAD --oneline

# Geänderte Dateien
git diff main..HEAD --stat

# Konflikte prüfen
git merge-base HEAD main
git diff $(git merge-base HEAD main)..HEAD
```

## Schritt 3: Entscheidung — 4 Optionen

### Option A: Direkt mergen
Wann: Kleines Feature, vollständig getestet, kein Review nötig.
```bash
git checkout main
git merge --no-ff <branch> -m "feat: [was]"
git push origin main
git branch -d <branch>
```

### Option B: Pull Request öffnen
Wann: Review gewünscht, öffentliches Repo, Team-Kontext.
```bash
gh pr create --title "[Titel]" --body "..."
# Branch bestehen lassen bis PR gemergt
```

### Option C: Branch behalten
Wann: Feature pausiert, wird später weitergeführt.
```bash
git stash  # falls uncommitted changes
git push origin <branch>  # remote backup
# Kein Merge
```

### Option D: Branch verwerfen
Wann: Ansatz falsch, wird neu gemacht.
```bash
# Erst sicherstellen dass nichts Wertvolles verloren geht
git log --oneline  # letzte Chance zu prüfen
git checkout main
git branch -D <branch>
git push origin --delete <branch>  # falls remote existiert
```

## Schritt 4: Cleanup (nur nach erfolgreichem Merge)

```bash
# Lokalen Branch löschen
git branch -d <branch>

# Remote Branch löschen
git push origin --delete <branch>

# Aufräumen
git remote prune origin
```

## Worktree-Kontext

Falls in einem Worktree:
```bash
# Worktree-Status prüfen
git worktree list

# Worktree entfernen (nur nach Merge)
git worktree remove <path>
```

## Checkliste vor Merge

- [ ] Alle Tests grün (lokal ausgeführt, nicht nur "sollten sein")
- [ ] Kein Debug-Code, keine print()-Statements
- [ ] Commit-Messages sauber (kein "WIP", kein "fix stuff")
- [ ] Keine sensiblen Daten im Diff
- [ ] Merge-Strategie gewählt (A/B/C/D)

## Häufiger Fehler

Branch verwerfen bevor getestet wurde dass main noch funktioniert. Immer:
```bash
git checkout main && pytest  # Main noch gesund?
```
