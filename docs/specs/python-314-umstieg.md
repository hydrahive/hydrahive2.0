# Umstieg auf Python 3.14 (Ubuntu 26.04)

Task bee768be. Stand 12.10.2026.

## Problem

Prod läuft auf Ubuntu 26.04.1, HydraHive aber noch auf Python 3.12. Dieses 3.12
stammt aus den alten 24.04-Paketen und liegt in keinem Archiv mehr
(`python3.12 3.12.3-1ubuntu0.15`, nur noch in `/var/lib/dpkg/status`).
`apt autoremove` würde es entfernen, dann startet nichts mehr. So ist es auf
wks197 schon passiert.

Der Grund: Die Installer bevorzugen 3.12 fest.

| Stelle | heute |
|---|---|
| `installer/lib/python-venv.sh` `hh_pick_python` | 3.12 > 3.13 > 3.11 > python3 |
| `installer/modules/00-deps.sh` | installiert `python3.12 python3.12-venv`, sonst deadsnakes |
| `installer/modules/76-searxng.sh` | fest `/usr/bin/python3.12`, baut venv nur, wenn es fehlt |
| hydralink `installer/modules/20-agentlink.sh` `pick_python` | 3.12 > 3.13 > 3.11 > python3 |
| Modul opentor `extension/install.sh` | `python3 -m venv` nur, wenn `bin/python` fehlt, ohne `--clear` |
| `installer/lib/graphify.sh`, `code_graph_install.py` | baut venv nur, wenn `bin/graphify` fehlt |
| CI `pytest.yml` | `python-version: "3.12"` |

## Ist-Stand der Rechner (nur lesend geprüft)

| Rechner | System | Kern | hydralink | SearXNG |
|---|---|---|---|---|
| Prod (.2) | 26.04, python3 = 3.14 | 3.12 | 3.12 | 3.12 |
| wks197 | 26.04, nur 3.14 | 3.14 (seit 03.10., läuft) | 3.14 | nicht installiert |
| hydratest | 24.04, python3 = 3.12 | 3.12 | 3.12 | 3.12 |

Auf Prod hängen außerdem an 3.12: graphify-venv, opentor-venv, die Voice-Bridge
(nutzt das Kern-venv) und `voice-pe/.platformio/penv` (ESPHome-Werkzeug im
Projekt-Workspace, nicht Teil von HydraHive). Die Python-Prozesse in den
Docker-Containern haben ihr eigenes Python und sind nicht betroffen.

Belege, dass 3.14 trägt: wks197 läuft seit dem 03.10. auf 3.14 (inkl.
`aioesphomeapi`, `playwright`), die Test-Suite hier läuft auf 3.14.

## Lösung

### Regel für die Interpreterwahl

Der Installer nimmt das **System-Python der Distribution**, sofern es
mindestens 3.12 ist (`requires-python >= 3.12`), und zwar **aufgelöst**:
`/usr/bin/python3` → `/usr/bin/python3.14`.

Warum aufgelöst: Ein venv aus `/usr/bin/python3` verlinkt `bin/python` auf
`/usr/bin/python3`. Wechselt die Distribution später auf 3.16, läuft das venv
still mit dem falschen Interpreter und findet seine Pakete nicht mehr (so fiel
SearXNG vom 29.08. bis 26.09.2026 aus). Aus `/usr/bin/python3.14` gebaut,
zeigt `bin/python` ins Leere, sobald 3.14 verschwindet. Das erkennt die
vorhandene Prüfung `hh_venv_needs_rebuild` und baut neu.

Reihenfolge in `hh_pick_python`:
1. `HH_PYTHON` (Override wie bisher)
2. `/usr/bin/python3` aufgelöst, wenn Version ≥ 3.12
3. sonst `/usr/bin/python3.13`, `/usr/bin/python3.12` (z. B. 22.04 + deadsnakes)

Auf 24.04 ändert sich dadurch nichts: python3 ist dort 3.12, die Version passt,
kein Neubau. Auf 26.04 ergibt sich 3.14, und das vorhandene venv wird beim
nächsten `update.sh` mit `--clear` neu gebaut.

### Änderungen

**Kern (`hydrahive2`)**
- `python-venv.sh`: neue Reihenfolge, Rückgabe aufgelöst.
- `00-deps.sh`: `python3 python3-venv python3-dev` statt `python3.12*`.
  deadsnakes nur noch, wenn das System-python3 älter als 3.12 ist.
- `76-searxng.sh`: Interpreter über `hh_pick_python`. Passt die Version des
  venv nicht (oder ist `bin/python` kaputt), wird es mit `--clear` neu gebaut.
  Wird auch von `update.sh` aufgerufen, wenn SearXNG installiert ist und das
  venv nicht passt.
- graphify (`graphify.sh` + `code_graph_install.py`): „vorhanden“ heißt künftig,
  dass `venv/bin/python` läuft und dieselbe Version wie das Kern-venv hat.
  Sonst Neubau mit `--clear`.
- `update.sh`: `hydra-voice-bridge.service` (nutzt Kern-venv und Kern-Code)
  wird vor einem Neubau des Kern-venv angehalten und nach dem Neustart von
  hydrahive2 wieder gestartet. Ohne Neubau wird sie bei jedem Update per
  `try-restart` mit neu gestartet. Heute läuft die Bridge nach Updates mit
  altem Stand im Speicher weiter.
- CI: `pytest.yml` testet 3.12 **und** 3.14 (Matrix). 24.04-Installationen
  (hydratest) bleiben auf 3.12.

**hydralink**: `pick_python` nach derselben Regel. Die Neubau-Logik bei
abweichender Version gibt es dort schon.

**Modul opentor**: `install.sh` baut das venv mit `--clear` neu, wenn
`bin/python` fehlt, nicht startet oder eine andere Version als das Kern-venv
hat. Version 0.1.2 → 0.1.3.

### Was nicht gemacht wird

- Kein deadsnakes auf 26.04. `requires-python` bleibt `>=3.12`.
- Die venvs in den Voice-Containern (Whisper, Piper) bleiben wie sie sind,
  sie haben ihr eigenes System-Python.
- `apt autoremove` ist nicht Teil dieses Umstiegs (laut Probelauf ~400
  Pakete, das sind vor allem 24.04-Reste). Das kommt als eigener Schritt
  mit eigener Liste.

## Folgen für Prod

- Der Neubau löscht alles im Kern-venv, was nicht aus `core/pyproject.toml`
  kommt. Auf Prod sind das `duckdb`, `matplotlib`, `pandas`, am 21.08. von Hand
  installiert. Im Code (Kern, Module, Plugins) wird keines davon importiert.
  Entscheidung offen, siehe unten.
- Auszeit beim Update: Kern-venv (811 MB) wird neu gebaut. Dauer wird im Test
  gemessen.
- Zurück, solange 3.12 noch installiert ist:
  `sudo HH_PYTHON=/usr/bin/python3.12 HL_PYTHON=/usr/bin/python3.12 bash /opt/hydrahive2/installer/update.sh`

## Etappen

1. Kern-PR: Interpreterwahl, 00-deps, SearXNG, graphify, Voice-Bridge-Neustart, CI-Matrix.
2. hydralink-PR: `pick_python`.
3. Modul-PR: opentor 0.1.3.
4. Tests:
   - frischer `images:ubuntu/26.04`-Container: Installer vom Branch → alle
     venvs auf 3.14, Dienste aktiv, Websuche liefert Treffer, Code-Graph baut.
   - Prod nachstellen: 26.04-Container, 3.12 aus deadsnakes, mit `main` und
     `HH_PYTHON=/usr/bin/python3.12` installiert. Dann `update.sh` vom Branch
     → alles auf 3.14. Dann 3.12 entfernen, Neustart → alles läuft.
   - hydratest (24.04): `update.sh` vom Branch → kein Neubau.
   - Gegenprobe: Mit `main` statt Branch bleibt im nachgestellten Prod alles
     auf 3.12 und fällt nach Entfernen von 3.12 aus.
5. Prod (macht Till): `update.sh`, danach Admin → Module → OpenTor
   „Aktualisieren“. Ich prüfe lesend: alle venvs 3.14, alle Dienste aktiv,
   Websuche, Code-Graph, Voice-Bridge.
6. 3.12 von Prod entfernen: Skript `python312-entfernen.sh` (ohne Argument
   Probelauf, mit `--los` ausführen). Es bricht ab, solange noch ein venv
   oder Prozess unter `/opt`, `/var/lib/hydrahive2`, `/srv/fast/hydrahive2`
   auf 3.12 zeigt, und entfernt dann nur die `python3.12*`/`libpython3.12*`-Pakete.

## Entscheidungen (Till, 12.10.2026)

1. `duckdb`, `matplotlib`, `pandas` fallen weg. Der Neubau des Kern-venv
   übernimmt sie nicht.
2. Die CI testet 3.12 und 3.14 (Matrix).
3. `voice-pe/.platformio/penv` wird gebraucht und vor Etappe 6 auf 3.14 neu
   gebaut. Das Entfernen-Skript prüft es mit.
