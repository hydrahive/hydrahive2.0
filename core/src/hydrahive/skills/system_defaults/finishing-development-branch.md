---
name: finishing-development-branch
description: Strukturierter Abschluss eines Feature-Branches – erst Tests und CI, dann Entscheidung (PR/Merge/behalten), dann Aufräumen. Verwerfen nur auf ausdrücklichen Wunsch, Worktrees nie mit --force entfernen.
when_to_use: Wenn ein Feature-Branch fertig sein könnte, vor jedem Merge, wenn du „das kann ich jetzt mergen“ denkst, und beim Aufräumen von Worktrees unter _work/wt/.
tools_required: [shell_exec]
---

# Feature-Branch abschließen

> Überarbeitet nach „finishing-a-development-branch“ aus Superpowers v7.0.2 (github.com/obra/superpowers, MIT, © Jesse Vincent).

## Reihenfolge ist Pflicht

Entscheidung **nach** Tests und CI, nicht davor. Aufräumen **nach** dem Merge, nicht vorher.

## Schritt 1: Tests und CI prüfen

```bash
# Lokal nur gezielt (die Platte ist langsam) – die Tests der geänderten Bereiche
cd core && PYTHONPATH=src pytest -q tests/test_<bereich>*.py

# Maßgeblich ist die CI des PRs – alle Jobs grün, auf dem aktuellen Head
gh pr checks <nr>
```

**Stopp, wenn etwas rot ist.** Erst beheben, dann weiter. Ein Test, der auch auf anderen Branches wackelt, ist kein Freibrief: Ursache nachstellen und den Test reparieren (eigener PR), nicht „Rerun bis grün“.

## Schritt 2: Branch-Stand prüfen

```bash
git fetch -q origin
git log --oneline origin/main..HEAD          # eigene Commits
git rev-list --count HEAD..origin/main       # wie weit hinter main?
git diff --stat origin/main...HEAD           # geänderte Dateien
```

Liegt der Branch hinter main: main einmergen, Konflikte lösen, betroffene Tests erneut laufen lassen, pushen, CI abwarten.

## Schritt 3: Entscheidung

Zeig diese Auswahl knapp; die Entscheidung über das Zusammenführen trifft der Nutzer bzw. gilt die vereinbarte Regel.

**1. Pull Request (Standard in HydraHive)**
```bash
gh pr create --base main --title "<typ(bereich): kurz>" --body-file <datei>
```
Review durch hydrahive-reviewer; bei Auth, Root, Verteilung oder Schreibzugriffen zusätzlich hydrahive-security-reviewer. Merge **per Merge-Commit** und nur bei grüner CI:
```bash
gh pr merge <nr> --merge --match-head-commit "$(gh pr view <nr> --json headRefOid -q .headRefOid)"
```

**2. Branch behalten** – Arbeit pausiert. Alles committen und pushen (Sicherung auf dem Server), Worktree bleibt stehen.

**Kein „Verwerfen“-Angebot in der Auswahl.** Fertige, getestete Arbeit wegzuwerfen gehört nicht neben „Mergen“.

### Nur wenn der Nutzer ausdrücklich verwerfen will

Erst bestätigen lassen und dabei nennen, was verloren geht:

```
Das löscht endgültig:
- Branch <name> (lokal und auf GitHub)
- Commits: <liste>
- Worktree <pfad> samt nicht committeter Dateien
Bitte mit „verwerfen“ bestätigen.
```

Erst nach genau dieser Bestätigung: Worktree aufräumen (Schritt 4), dann `git branch -D <name>` und `git push origin --delete <name>`.

## Schritt 4: Aufräumen (nach Merge oder bestätigtem Verwerfen)

Aus dem Haupt-Checkout heraus, nie aus dem Worktree selbst:

```bash
cd /var/lib/hydrahive2/workspaces/projects/<projekt>/hydrahive2 || exit 1
git worktree remove /absoluter/pfad/_work/wt/<name>
git worktree prune
git branch -d <branch>            # -d, nicht -D: verweigert ungemergte Branches
```

**Verweigert `git worktree remove`** („contains modified or untracked files“): Dort liegen Dateien, die es nirgends sonst gibt – Pläne, Notizen, Probe-Logs. **Nie von dir aus `--force`.** Zeigen, was dort liegt, und fragen:

```bash
git -C /absoluter/pfad/_work/wt/<name> status --porcelain -uall
```

Test-Branches (z. B. `test/u4p-*`) erst löschen, wenn die Probe ausgewertet und festgehalten ist.

## Checkliste vor dem Merge

- [ ] CI des PRs komplett grün, auf dem aktuellen Head
- [ ] Review(s) durch; „muss“-Befunde erledigt, „sollte“ geprüft (siehe receiving-code-review)
- [ ] Kein Debug-Code, keine sensiblen Daten im Diff
- [ ] System-Skills geändert? `_history.json` neu erzeugt (`python3 scripts/update_skill_history.py`)
- [ ] Commit-Nachrichten sauber und auf Deutsch, keine @-Erwähnungen
- [ ] Task-Notiz mit PR-Nummer und Merge-Commit

## Ausreden und Wirklichkeit

| Ausrede | Wirklichkeit |
|---|---|
| „Lokal grün reicht“ | Die CI läuft auf dem echten Stand von main. Erst sie zählt. |
| „Der Test wackelt eh“ | Dann Ursache finden und den Test reparieren – nicht übergehen. |
| „Schnell --force, da ist nichts Wichtiges“ | Du weißt nicht, was dort liegt. Erst nachsehen und fragen. |
| „Verwerfen als Option schadet nicht“ | Neben „Mergen“ verleitet es dazu, fertige Arbeit wegzuwerfen. |
| „Merge-Commit ist egal“ | HydraHive mergt per Merge-Commit; der Verlauf bleibt nachvollziehbar. |
