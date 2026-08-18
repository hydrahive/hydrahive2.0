# Ubuntu 26.04 LTS Support

**Status:** Sondierung abgeschlossen — Installer-Umbau offen
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

### ENTWARNUNG: Dependency-Stack trägt unter Python 3.14

**Auf echter Hardware verifiziert (Testserver 192.168.178.174, Ubuntu 26.04 LTS,
Python 3.14.4, 2026-08-19).**

`pip install -e core/` läuft vollständig durch. Alle C-Extension-Pakete, die als
Hauptrisiko galten, liefern fertige `cp314`-Wheels — nichts muss aus Quellen
gebaut werden:

| Paket | Version unter 3.14 |
|---|---|
| `asyncpg` | 0.31.0 |
| `bcrypt` | 5.0.0 |
| `cryptography` | 48.0.1 |
| `uvloop` | 0.22.1 |
| `httptools` | 0.8.0 |
| `playwright` | 1.62.0 |
| `litellm` | 1.97.0 |
| `matrix-nio` | 0.25.2 |
| `discord.py` | 2.7.1 |
| `fastapi` | 0.136.3 (innerhalb `<0.137`-Deckel) |

**Testsuite: 2031 bestanden, 0 Fehler, 5 übersprungen (145 s).**

Erster Lauf zeigte 4 Fehler in `tests/test_vm_passthrough.py`. Ursache war **nicht**
Python 3.14, sondern fehlendes `qemu-img` auf dem frischen Server. Nach
`apt-get install qemu-utils` sind alle 15 Tests der Datei grün. Nebenbefund:
`qemu-utils` ist eine faktische Testabhängigkeit, die in `00-deps.sh` fehlt.

Damit ist Option A (venv auf System-Python 3.14) tragfähig. Das Restrisiko liegt
nur noch im Installer selbst.

### Weitere Abweichungen

Alle Werte auf dem Testserver mit `apt-cache policy` verifiziert:

| Thema | 24.04 | 26.04 | Bewertung |
|---|---|---|---|
| PostgreSQL | 16 | **18** (`18+290ubuntu1`) | `48-postgres.sh` ermittelt `PG_VER` dynamisch → ok |
| pgvector | `postgresql-16-pgvector` | **`postgresql-18-pgvector` 0.8.1-2 vorhanden** | ok, kein Handlungsbedarf |
| sudo | sudo | **sudo-rs 0.2.13** | Flag-Kompatibilität der Skripte prüfen |
| Node.js | 20 (gepinnt) | Distro liefert **22.22** | `00-deps.sh` pinnt `setup_20.x`; Node 20 läuft 2026 aus dem Support |
| nginx | — | 1.28.3 | ok |
| ffmpeg | — | 8.0.1 | Major-Sprung (7 → 8), Voice-Pipeline gegenprüfen |
| sshpass | — | 1.10 | ok |
| `qemu-utils` | implizit da | **fehlt** | faktische Abhängigkeit, in `00-deps.sh` ergänzen |
| Voice-LXC | `images:ubuntu/24.04` | fest verdrahtet | `55-voice.sh` Zeilen 115, 236 |
| CI | `python-version: "3.12"`, `node-version: "20"` | — | `.github/workflows/pytest.yml` |
| ruff | `target-version = "py312"` | — | `core/pyproject.toml` |

## Wie (Vorgehen)

Reihenfolge bewusst: **erst messen, dann bauen.**

### Phase 1 — Sondierung ✅ ABGESCHLOSSEN (2026-08-19)

Auf Testserver 192.168.178.174 durchgeführt. Ergebnis: Stack trägt unter 3.14,
Testsuite vollständig grün. Option A ist tragfähig, Phase 2 kann starten.

### Phase 2 — Installer versions-agnostisch (offen)

- Interpreter-Erkennung statt hartem `python3.12`: höchste verfügbare Version aus
  3.12 / 3.13 / 3.14 wählen (alle drei nachweislich tragfähig)
- `python3.12-venv` → passendes `pythonX.Y-venv` zum erkannten Interpreter
- `qemu-utils` in `REQUIRED_PACKAGES` ergänzen
- Node-Pin überdenken: 26.04 liefert bereits 22.22; `setup_20.x` ist überholt
- `55-voice.sh`: LXC-Image nicht mehr fest auf 24.04
- Distro-Erkennung über `VERSION_ID`/`UBUNTU_CODENAME` statt impliziter Annahmen
- deadsnakes-Fallback: greift nur für < 24.04, muss diese Grenze sauber prüfen

Ziel: **eine** Codebasis bedient 24.04 und 26.04. Bestandsinstallationen auf 24.04
werden nicht angefasst.

### Phase 2b — Verbleibende Unbekannte

Die Sondierung deckte Backend + Tests ab. Noch **nicht** verifiziert:

- **Frontend-Build** (`npm ci && npm run build`) unter Node 22 statt 20 —
  Vite 8 / TypeScript 6 / React 19
- **ffmpeg 8** in der Voice-Pipeline (24.04 hat 7) — Filter-/Flag-Kompatibilität
- **sudo-rs**: ob alle im Installer genutzten sudo-Aufrufe unterstützt werden
- **Vollständiger `install.sh`-Durchlauf** auf frischem 26.04

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
