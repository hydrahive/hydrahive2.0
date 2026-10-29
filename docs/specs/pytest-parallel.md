# Testreihe auf mehreren Kernen (pytest-xdist)

Task 2a02ca15. Stand 28.10.2026.

## Problem

Die Kern-Testreihe läuft nacheinander auf einem Kern:
- auf dem Hauptserver (24 Kerne) 8:20 min,
- in der CI je Job etwa 13 bis 14 min.

Jede Etappe braucht mehrere volle Läufe (Rot, Grün, Mutanten-Gegenprobe, Abschluss). Das ist der größte Zeitverlust
beim Arbeiten.

## Messung (28.10.2026, Hauptserver, main 64ec0733)

| Lauf | Dauer | Ergebnis |
|---|---|---|
| nacheinander (heute) | 8:20 min | 5139 grün |
| `-n 4` (wie ein GitHub-Rechner) | 2:26 min | 5163 grün |
| `-n 16` | 1:21–1:31 min | 5163 grün |
| `-n 24` | 1:15–1:29 min | 5163 grün |
| `-n 16`, Python 3.12 | 1:44 min | 5163 grün |

Zwei Tests wurden mit `-n` zufällig rot. Beides waren Fehler in den Tests, behoben in #641:
- Eine Attrappe las ihre Eingabe nicht.
- Ein Test ließ die gemeinsame `llm.json` liegen.

Jeder Arbeitsprozess hat schon heute einen eigenen Testordner (`tests/_isolation.py`, `mkdtemp` beim Laden). Die
Tests teilen sich also keine Daten zwischen den Prozessen.

## Änderung

1. `pytest-xdist` kommt zu den Abhängigkeiten in `core/pyproject.toml`, direkt neben `pytest`.
2. Beide pytest-Jobs der CI (3.14 und 3.12) laufen mit `-n auto`. Auf GitHub-Rechnern sind das 4 Prozesse.
3. **Kein** `-n` in `addopts`. Ein einzelner Test oder eine Datei läuft weiter ohne Startkosten für viele Prozesse.
   Die volle Reihe ruft man lokal mit `-n 16` auf.
4. Die Jobnamen bleiben unverändert, sie sind Pflicht-Checks im Branch-Schutz.

## Nicht Teil dieser Änderung

- Einige Tests brauchen Internet:
  - `test_searxng_venv` lädt `setuptools` von PyPI.
  - `test_module_install_flow` holt den echten Modul-Hub per `git pull`.
  - Bei einer Netzstörung am 28.10. wurden sie rot.
  - Das ist unabhängig von `-n` und kommt in einen eigenen Task.
- Frontend (vitest) läuft schon parallel.

## Prüfung

- Vertragstest: `pytest-xdist` steht in den Abhängigkeiten, beide CI-Jobs rufen pytest mit `-n auto` auf, die Namen
  bleiben gleich.
- Rot gegen `main`, grün danach. Mutanten auf den Vertragstest.
- CI-Dauer vorher und nachher im PR festhalten.
