# Distro-Upgrade 24.04 → 26.04 für HydraHive-Server

**Stand:** 2026-08-19 · Testserver `192.168.178.186` · Branch `feat/ubuntu-2604-support`

Dieses Dokument entsteht während des Testlaufs. Es beschreibt **noch nicht**
das freigegebene Vorgehen für den Produktivserver — das folgt, wenn der
Testserver das Upgrade überstanden hat.

## Warum ein Testlauf zwingend ist

`installer/update.sh` aktualisiert HydraHive, **fasst das venv aber nie an**:
es ruft direkt `.venv/bin/pip install -e core` und führt weder `00-deps.sh`
noch `30-python.sh` aus.

Auf 24.04 kommt `python3.12` aus dem **Ubuntu-Archiv** (`noble-updates/main`),
nicht von deadsnakes. Auf 26.04 existiert dieses Paket dort nicht mehr. Ein
`do-release-upgrade` entfernt den Interpreter also — und das venv zeigt
anschließend ins Leere.

**Folge: HydraHive startet nach dem Upgrade nicht mehr, und `update.sh`
repariert das nicht.** Genau dieselbe Klasse von Fehler hatten wir bei
HydraLink (venv-Zwitter nach Interpreter-Wechsel).

## Ausgangszustand des Testservers (vor dem Upgrade)

| Komponente | Version |
|---|---|
| OS | Ubuntu 24.04.4 LTS |
| Python | 3.12.3 (`noble-updates/main`) |
| venv | `executable = /usr/bin/python3.12` |
| Node.js | v20.20.2 |
| PostgreSQL | 16.14 (Cluster `16 main`, Port 5432) |
| nginx | 1.24.0 |
| ffmpeg | 6.1.1 |
| sudo | 1.9.15p5 (klassisch) |
| incus | `hydrahive2-stt`, `hydrahive2-tts` (beide RUNNING) |

HydraHive-Stand: `aa717132`, alle Dienste aktiv, API-Endpunkte 200.

**Erwartete Zielversionen auf 26.04** (auf dem 26er Testserver gemessen):
Python 3.14.4, PostgreSQL 18, Node 22.22, nginx 1.28.3, ffmpeg 8.0.1,
sudo-rs 0.2.13.

## Vorab-Ergebnis: 24.04-Regressionstest bestanden

Der Branch `feat/ubuntu-2604-support` wurde auf frischem 24.04 installiert —
**ohne Regression**. Alle Phasen liefen durch, kein `FEHLT`-Block, alle Dienste
aktiv, `/api/health`, Buddy, Agents, Projekte und AgentLink antworten mit 200.

Damit ist Akzeptanzkriterium 2 der Spec erfüllt: die Fixes brechen 24.04 nicht.

## Risiken beim Upgrade (Reihenfolge nach Schwere)

1. **venv zeigt auf gelöschten Interpreter** → Backend startet nicht.
   Betrifft `/opt/hydrahive2/.venv` und `/opt/hydralink/.venv`.
2. **PostgreSQL 16 → 18**: Ubuntu legt einen neuen Cluster an, der alte bleibt
   liegen. Ohne `pg_upgradecluster` zeigt der Dienst auf eine leere Datenbank.
3. **incus-Container**: `hydrahive2-stt`/`-tts` überstehen einen Distro-Wechsel
   des Hosts nicht zwangsläufig.
4. **sudo → sudo-rs**: verschärfte Syntaxprüfung (unser `requiretty`-Fix ist
   bereits drin, aber andere Dateien können betroffen sein).
5. **Node 20 → 22**: NodeSource-Repo-Eintrag zeigt weiter auf `setup_20.x`.
6. **ffmpeg 6 → 8**: zwei Major-Sprünge, Voice-Pipeline ungetestet.

## Vorgehen im Test

1. Ausgangszustand dokumentieren ✅ (siehe oben)
2. Prüfsumme fachlicher Daten sichern (Agenten, Projekte, Sessions) — damit
   nach dem Upgrade belegbar ist, dass nichts verloren ging
3. `do-release-upgrade` durchführen, Ausgabe vollständig protokollieren
4. Schadensaufnahme: welche Dienste starten, welche nicht
5. Reparaturen ableiten und in `update.sh` gießen
6. Runbook für den Produktivserver fertigstellen

## Offene Empfehlung für den Produktivserver

Vor jedem Upgrade des Produktivsystems: **vollständiges Backup bzw.
VM-Snapshot**, und einen Rückfallweg festlegen. Ein Distro-Upgrade ist nicht
zurückrollbar.

Ernsthaft zu prüfende Alternative: **neuen 26.04-Server aufsetzen und Daten
migrieren** statt in-place zu upgraden. Vorteile: kein Altlast-Zwitter, Testen
vor dem Umschalten möglich, alter Server bleibt als sofortiger Rückfallweg
stehen. Bei einem System mit PostgreSQL, incus-Containern und VMs ist das
üblicherweise der ruhigere Weg.
