# Ubuntu 26.04 LTS Support

**Status:** Planung / Sondierung
**Branch:** `feat/ubuntu-2604-support`
**Erstellt:** 2026-08-19
**Task:** f888b99f

## Was

HydraHive muss auf Ubuntu 26.04 LTS ("Resolute Raccoon", Release 23.04.2026)
fehlerfrei installierbar und lauffähig sein. Aktuell bricht `installer/install.sh`
auf 26.04 ab.

## Warum

24.04 LTS bleibt zwar bis 2029 im Standard-Support, aber 26.04 ist ab sofort die
LTS-Version, die Neukunden auf frischer Hardware installieren. Ohne Anpassung
scheitert dort jede Erstinstallation — und zwar hart, nicht mit Degradation.

## Befund (verifiziert 2026-08-19)

### Blocker: Python 3.12 existiert auf 26.04 nicht

26.04 liefert **Python 3.14** als Default-Interpreter. Es gibt **kein**
`python3.12`-Paket:

- nicht im Ubuntu-Archiv (main/universe)
- nicht über deadsnakes — das PPA liefert grundsätzlich nur Versionen, die die
  Distribution nicht selbst mitbringt; für `resolute` ist 3.14 ausdrücklich
  ausgenommen

Betroffene Stellen:

| Datei | Zeile | Problem |
|---|---|---|
| `installer/modules/00-deps.sh` | 11–12 | `python3.12`, `python3.12-venv` in `REQUIRED_PACKAGES` → `apt-get install` scheitert |
| `installer/modules/00-deps.sh` | 42 | deadsnakes-Fallback greift nur für "Ubuntu < 24.04", hilft hier nicht |
| `installer/modules/30-python.sh` | 11 | `python3.12 -m venv "$VENV"` → Kommando existiert nicht |

Folge: Installation bricht in Phase 1 (deps) bzw. 3 (python) ab. Kein Workaround
ohne Codeänderung.

### Offene Risiken (noch nicht verifiziert)

Der eigentliche Risikoblock ist **nicht** der Installer, sondern die Frage, ob der
Dependency-Stack unter Python 3.14 trägt. Besonders zu prüfen sind Pakete mit
C-Extensions und enger Interpreter-Kopplung:

- `bcrypt`, `cryptography` (C-Extensions)
- `asyncpg` (C-Extension, eigene Event-Loop-Integration)
- `litellm`, `anthropic` (großer Abhängigkeitsbaum)
- `playwright` (Browser-Binaries + Python-Bindings)
- `matrix-nio`, `discord.py` (async, ältere Codebasen)
- `uvicorn[standard]` (uvloop/httptools — C-Extensions)

### Weitere Abweichungen

| Thema | 24.04 | 26.04 | Bewertung |
|---|---|---|---|
| PostgreSQL | 16 | 18 | `48-postgres.sh` ermittelt `PG_VER` dynamisch → vermutlich ok; `postgresql-18-pgvector` verifizieren |
| sudo | sudo | **sudo-rs** | Flag-Kompatibilität der Skripte prüfen |
| Node.js | 20 (gepinnt) | — | `00-deps.sh` pinnt `setup_20.x`; Node 20 läuft 2026 aus dem Support |
| Voice-LXC | `images:ubuntu/24.04` | fest verdrahtet | `55-voice.sh` Zeilen 115, 236 |
| CI | `python-version: "3.12"`, `node-version: "20"` | — | `.github/workflows/pytest.yml` |
| ruff | `target-version = "py312"` | — | `core/pyproject.toml` |

## Wie (Vorgehen)

Reihenfolge bewusst: **erst messen, dann bauen.**

### Phase 1 — Sondierung (keine Codeänderung)

26.04-Container hochziehen, `pip install -e core/` unter Python 3.14, volle
Testsuite (1937 Tests). Ergebnis entscheidet über Phase 2.

Diese Phase ist billig und beantwortet die einzige wirklich offene Frage. Ohne sie
besteht das Risiko, den Installer umzubauen und erst danach festzustellen, dass ein
Kernpaket unter 3.14 nicht startet.

### Phase 2 — Installer versions-agnostisch

Abhängig vom Ergebnis aus Phase 1:

- Interpreter-Erkennung statt hartem `python3.12` (Reihenfolge: 3.12 → 3.13 → 3.14,
  bzw. was Phase 1 als tragfähig erweist)
- Distro-Erkennung über `VERSION_ID`/`UBUNTU_CODENAME` statt impliziter Annahmen
- PG-, Node- und LXC-Image-Versionen dynamisch bzw. konfigurierbar

Ziel: **eine** Codebasis bedient 24.04 und 26.04. Bestandsinstallationen auf 24.04
werden nicht angefasst.

### Phase 3 — CI + Doku

Testmatrix um 26.04/Python 3.14 erweitern, `installer/README.md` und
`requires-python` nachziehen.

## Akzeptanzkriterien

1. `installer/install.sh` läuft auf frischem Ubuntu 26.04 LTS ohne Fehler durch.
2. `installer/install.sh` läuft weiterhin auf 24.04 LTS durch (keine Regression).
3. Backend startet, Frontend baut, Testsuite grün — auf beiden Distributionen.
4. CI prüft beide Konstellationen.
5. Bestehende 24.04-Instanzen brauchen **keine** Migration.

## Nicht Teil dieser Spec

- Migration bestehender 24.04-Instanzen auf 26.04 (eigener Vorgang, falls gewünscht)
- Abkündigung von 22.04 (`installer/README.md` nennt es noch)
- Voice-Bridge-Themen (separat, aktuell pausiert)

## Offene Entscheidung

Support-Matrix: 24.04 **und** 26.04 dauerhaft parallel (doppelte Testmatrix), oder
26.04 als alleiniges Ziel mit definiertem Migrationspfad? Diese Spec geht bis zur
Klärung vom Parallelbetrieb aus, weil er Bestandsinstallationen schützt.
