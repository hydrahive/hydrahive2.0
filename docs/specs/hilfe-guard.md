# Hilfe-Guard: Nutzersichtbare Änderungen bringen ihre Hilfe mit

> **Status:** FREIGEGEBEN (Till, 28.11.2026: „ok freigegeben“).
> **Anlass:** Till am 28.11.2026: „Vielleicht sollte man das mal automatisieren, dass nach jeder Erweiterung oder
> Änderung das Handbuch angepasst wird.“

## 1. Ausgangslage (gemessen 28.11.2026)

Wiki und PDF-Handbuch werden schon automatisch gebaut, und zwar aus den Hilfe-Artikeln:
- `.github/workflows/wiki.yml` startet bei jedem Push auf `main`, der die Hilfe ändert, außerdem täglich und von Hand.
- Ziel und Aufbau stehen in `hydrahive2-modules/ziele/wiki-automatik.md`.

Das Wiki ist also genau so aktuell wie die Artikel selbst. **Die Artikel pflegt aber niemand automatisch nach.**

Die Zahlen beziehen sich auf die letzten 30 Tage auf `main` (29.10.–28.11.2026). Gezählt sind gemergte PRs, also Merge-Commits im Kern und Squash-Commits mit `(#N)` im Modul-Repo. Als nutzersichtbar zählt ein PR, wenn er Dateien nach den Mustern aus Abschnitt 2 ändert.

| Repo | PRs | davon nutzersichtbar | davon mit Hilfe-Änderung |
|---|---|---|---|
| Kern `hydrahive2.0` | 139 | 53 | 6 (11 %) |
| Module `hydrahive2-modules` | 181 | 87 | 2 (2 %) |

Die Zählung erkennt nutzersichtbare PRs nur am Dateimuster und ist deshalb eine Schätzung. Unter den 53 Kern-PRs sind auch reine Fixes, die keine neue Hilfe brauchen. Die Größenordnung ist trotzdem eindeutig.

Beispiele seit dem 22.11. ohne Hilfe:
- Agenten-Bereiche (#789–#795): neuer Reiter „Was darf der Agent?“.
- Werkzeug- und Skill-Katalog (#779–#788): Schalter „Werkzeuge bei Bedarf suchen“.
- Update mit Sicherung und Rückweg (#753–#762).

Nachgezogen werden diese Lücken in `docs/plans/hilfe-nachziehen-2026-11.md`.

## 2. Regel

Ein PR ist **nutzersichtbar**, wenn er mindestens eine dieser Dateien ändert. Tests (`*.test.*`, `tests/`) zählen nicht.

| Repo | Muster |
|---|---|
| Kern | `frontend/src/features/**/*.tsx`, `frontend/src/shared/**/*.tsx`, `frontend/src/i18n/locales/de/*.json`, `installer/update*.sh`, `installer/lib/update-*.sh`, `installer/install*.sh` |
| Module | `<modul>/frontend/**/*.tsx`, deutsche Texte `<modul>/frontend/**/*i18n*.ts` bzw. `*I18n*.ts` (ohne `*.en.ts`) und `<modul>/frontend/**/texts*.de.ts`, `<modul>/manifest.json` (nur wenn sich `name`, `description`, `icon`, `nav_group`, `vault` oder `agent_areas` ändern) |

Ein nutzersichtbarer PR braucht **eine geänderte oder neue Hilfe-Datei**:
- Kern: `frontend/src/i18n/help/de/*.md`
- Module: `<modul>/frontend/help/de/*.md` desselben Moduls

**Ausnahme:** Die PR-Beschreibung enthält eine Zeile `Keine Hilfe nötig: <Begründung>` mit mindestens 10 Zeichen Begründung. Typisch sind ein reiner Bugfix ohne neue Bedienung, eine Stilkorrektur oder ein interner Umbau. Die Ausnahme ist damit begründet und im PR nachlesbar.

**Welcher Artikel passt?** Der Guard nennt ihn, damit niemand suchen muss:
- Kern: aus der Zuordnung Ordner unter `features/` → Hilfe-Thema. Die Zuordnung wird aus den `HelpButton topic="…"`-Stellen im Code gelesen, z. B. `features/communication` → `communication.md`.
- Ohne Treffer nennt er „passenden Artikel unter frontend/src/i18n/help/de/ wählen oder neu anlegen“.
- Module: immer `<modul>/frontend/help/de/`.

**Korrektur 28.11.2026 (Review modules #478):** Die erste Fassung nannte für Module `frontend/i18n/de*` und die
Manifest-Felder `routes`, `nav`, `settings`. Beides gibt es im Repo nicht: Die Texte liegen in `frontend/i18n*.ts` bzw.
`texts.de.ts` (auch Teildateien wie `texts.ghost.de.ts`, `seatsI18n.ts`), und das Manifest kennt nur die Felder aus
`core/src/hydrahive/modules/manifest.py`. Korrigiert in modules #479. Bekannte Grenze: Textdateien ohne Namensmerkmal
(z. B. `tonstudio/frontend/errors.ts`) erkennt der Guard nicht.

## 3. Modus

- **Start mit `HILFE_GUARD_MODE=warn`.** Ein Verstoß erscheint als Warnung im Check und in der Zusammenfassung, der Check bleibt grün. So wurde es auch beim Fix-Test-Guard gemacht.
- **Nach zwei Wochen auswerten** (eigener Task): Wie oft hat er angeschlagen, und wie oft war die Ausnahme berechtigt?
- **Erst dann `block`**, nach Tills Entscheidung.

## 4. Fehlermeldung (was, warum, wie beheben)

```
Hilfe fehlt: 4 nutzersichtbare Datei(en) geändert (features/agents/areas/AreaSwitch.tsx, …), keine Hilfe-Datei.
WARUM: Wiki und PDF-Handbuch entstehen aus den Hilfe-Artikeln – ohne Artikel-Änderung bleibt das Handbuch alt
       (Regel docs/specs/hilfe-guard.md).
BEHEBEN: frontend/src/i18n/help/de/agents.md ergänzen
         oder in die PR-Beschreibung schreiben: „Keine Hilfe nötig: <Begründung>“.
```

## 5. Umsetzung

- **Skript:** `scripts/check_help_updated.py` im Kern, aufgebaut wie `scripts/check_fix_has_test.py`:
  - liest nur Git-Daten und Umgebungsvariablen
  - kein Netzwerkzugriff, schreibt nichts
- **Workflow:** `.github/workflows/hilfe-guard.yml`
  - Trigger `pull_request` (opened, edited, synchronize, reopened)
  - `permissions: contents: read`
  - PR-Texte nur über `env`, nie direkt in `run:` (Schutz vor Script-Injection)
- **Modul-Repo:** eigene Kopie `scripts/check_help_updated.py` mit den Modul-Mustern, dazu `.github/workflows/hilfe-guard.yml`.
  - Eine gemeinsame Datei gibt es nicht, weil die Repos getrennt bauen.
  - Gleicher Meldungstext.
- **Agenten-Anweisung:** Im Baustein „Arbeitsweise“ des Projekt-Agenten, kurz im Skill `verification-before-completion`, steht ein Satz: Nutzersichtbare Änderung → Hilfe-Artikel im selben PR ergänzen. So schreibt der Agent die Hilfe gleich mit, statt erst die Warnung abzuwarten.

## 6. Nicht-Ziele

- Keine KI, die Hilfe-Texte selbst schreibt oder ändert. Der Guard prüft nur, ob etwas geändert wurde, nicht ob es gut ist. Das bleibt Sache des Reviews.
- Keine Prüfung englischer Artikel. Die Hilfe ist zuerst Deutsch, so steht es in `ziele/hilfe-aktuell.md`.
- Keine Prüfung des Discord-Handbuchs. Das ist ein eigenes Thema (Tasks 46bb94cf, d18cbfb7).

## 7. Sicherheit

- `pull_request`, nicht `pull_request_target`. Kein Secret, keine Schreibrechte.
- PR-Titel und -Beschreibung nur als Umgebungsvariablen.

## 8. Abnahme

| # | Prüfung |
|---|---|
| HG1 | Tests Kern: nutzersichtbar erkannt (je Muster), Tests und Doku allein lösen nichts aus, Hilfe-Datei gefunden → ok, Ausnahme mit genügend bzw. zu kurzer Begründung, Warn- und Blockmodus (Exit-Code) |
| HG2 | Artikel-Vorschlag: `features/communication/X.tsx` → `communication.md` (Zuordnung aus `topic=`), unbekannter Ordner → allgemeiner Hinweis |
| HG3 | Tests Modul-Repo: Modul-Muster, Hilfe desselben Moduls nötig (Hilfe eines anderen Moduls zählt nicht), Manifest nur bei sichtbaren Feldern (name, description, icon, nav_group, vault, agent_areas) |
| HG4 | Probelauf gegen die echten PRs der letzten 30 Tage stimmt mit der Tabelle in Abschnitt 1 überein (Abweichungen erklärt) |
| HG5 | Workflows: `pull_request`, `contents: read`, PR-Texte nur über env; Lauf auf einem Probe-PR zeigt die Warnung |
| HG6 | Satz in der Arbeitsweise bzw. im Skill ergänzt, `_history.json` aktualisiert |
