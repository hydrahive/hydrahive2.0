# Fix-Test-Guard: jeder Fix bringt einen Test mit

Harness-Punkt 4 (Task 3d40fce8), Kurs L10 „Review Feedback Promotion“: Jede neue Fehlerart, die ein Review oder
ein Live-Befund findet, wird als automatischer Test verankert – bevor der Fix gemergt wird.

## Ausgangslage (gemessen 10.11.2026)

Letzte 30 Tage auf `main`: 99 Fix-Commits mit Produktivcode, davon 71 mit Test (72 %). Erkennung über Betreff und
Dateinamen, daher eine Schätzung. Ohne Test waren vor allem Installer-/Bash-, Mac- und Layout-Fixes.

## Regel

Ein PR gilt als **Fix**, wenn sein Titel, ein Commit-Betreff oder der Branch-Name mit `fix`, `hotfix` oder
`bugfix` beginnt (z. B. `fix(shell): …`, `fix: …`, Branch `fix/…`).

Ein Fix-PR, der **Produktivcode** ändert (`.py`, `.ts`, `.tsx`, `.sh`, `.mjs`, `.js` außerhalb von Tests),
braucht **eine geänderte oder neue Testdatei**: `test_*.py`, `*.test.ts(x)`, `*.spec.ts(x)` oder eine Datei unter
einem `tests/`-Ordner. `*_test.py` zählt bewusst nicht: Das Muster kommt im Repo nicht vor und würde Skripte wie
`check_fix_has_test.py` fälschlich als Test werten (echter Fund im ersten CI-Lauf, PR #696).

Fix-Erkennung nur als Präfix wie in Commit-Konventionen (`fix:`, `fix(scope):`, `fix …`). Titel wie
„Fix-Test-Guard“ oder „Fixtures …“ sind kein Fix (ebenfalls Fund aus PR #696).

**Ausnahme:** Die PR-Beschreibung enthält eine Zeile `Kein Test: <Begründung>` (mindestens 10 Zeichen
Begründung). Die Ausnahme ist damit begründet und im PR nachlesbar.

## Modus

`FIX_TEST_GUARD_MODE=warn` (Start, Tills Entscheidung 10.11.2026): Verstöße erscheinen als Warnung im Check und in
der Zusammenfassung, der Check bleibt grün. Nach zwei Wochen wird ausgewertet (eigener Task), wie oft er anschlug
und ob die Funde berechtigt waren. Erst dann ggf. `block`.

## Fehlermeldung (L10: was, warum, wie beheben)

```
Fix ohne Test: 3 Produktivdatei(en) geändert (…), keine Testdatei.
WARUM: Ein Fix ohne Test kann unbemerkt wiederkommen (Kurs L10, Regel docs/specs/fix-test-guard.md).
BEHEBEN: Test ergänzen, der ohne den Fix rot ist (test_*.py, *.test.ts …),
         oder in die PR-Beschreibung schreiben: „Kein Test: <Begründung>“.
```

## Sicherheit

- Trigger `pull_request` (nicht `pull_request_target`), `permissions: contents: read`.
- PR-Titel, -Beschreibung und Branch-Name kommen nur über Umgebungsvariablen ins Skript, nie in die `run:`-Zeile
  (Schutz vor Script-Injection über PR-Texte).
- Das Skript liest nur Git-Daten und gibt Text aus; keine Netzwerkzugriffe, kein Schreiben.

## Skills

`code-review` und `verification-before-completion` bekommen die Regel als Schritt: Fund → erst ein Test, der ohne
Fix rot ist, dann der Fix.

## Akzeptanz

- Tests decken ab: Fix-Erkennung (Titel, Commit, Branch, kein Fix), Test-Erkennung je Muster, Doku-/Config-only
  ohne Warnung, Ausnahme mit/ohne ausreichende Begründung, Warn- vs. Blockmodus (Exit-Code).
- Probelauf gegen die echten Fix-Commits der letzten 30 Tage stimmt mit der Messung oben überein.
- Kein Eingriff in Laufzeit oder Dienst, kein Neustart.
