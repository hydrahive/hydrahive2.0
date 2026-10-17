# Modul-Install, -Update und -Deinstallation laufen zu Ende, auch ohne offenen Browser

## Problem (geprüft am 17.10. auf hydratest)

Admin → Module → „Update verfügbar“ startet `POST /api/admin/modules/{id}/update`. Die Route gibt einen
SSE-Stream zurück, der den Generator `installer.update()` **direkt** durchläuft. Ein Generator macht nur weiter,
solange jemand liest. Trennt der Browser die Verbindung (Tab zu, anderes Menü, Netz weg), bricht Starlette die
Iteration ab. Der Ablauf bleibt dann mitten drin stehen.

Nachgestellt mit `curl -m 2` gegen `example`:
- „Dateien sicher ersetzt“ wurde noch ausgeführt.
- Der Frontend-Build lief im bereits gestarteten Unterprozess weiter („built in 10.63s“).
- `_request_restart()` wurde **nie** erreicht: Es gab keinen `.restart_request`, und der Dienst lief weiter.

Folge: Die neuen Moduldateien liegen schon da und das Frontend ist neu gebaut, aber das Backend läuft mit dem alten
Stand weiter. Neue Routen antworten mit 404 (beim Studio-Update so passiert). Das bleibt so bis zum nächsten
Neustart, den unbekannte Nutzer nicht selbst auslösen können.

Gleiches gilt für Install und Deinstallation. Zusätzlich können heute zwei Abläufe gleichzeitig laufen, etwa zwei
Tabs oder „Alle updaten“ plus ein Einzelklick. Beide bauen dann gleichzeitig das Frontend.

## Ziel

- Ein gestarteter Ablauf läuft **immer** bis zum Ende, auch wenn niemand zusieht. Am Ende steht der Neustart bzw.
  bei einem Fehler ein Eintrag im Log.
- Der Browser zeigt den Fortschritt wie bisher. Die Oberfläche und das Format des Streams ändern sich nicht.
- Es läuft höchstens ein Modul-Ablauf gleichzeitig. Ein zweiter Start bekommt eine klare Meldung.

## Lösung

Neue kleine Datei `core/src/hydrahive/modules/operations.py`:

- `start(kind, module_id, gen) -> Operation` startet einen **Daemon-Thread**. Dieser liest den Generator
  vollständig und hängt jede Zeile an die Operation an (Liste plus `threading.Condition`). Am Ende setzt er
  `done=True` oder `error=str(exc)`. Fehler werden mit `logger.exception` geloggt, wie bisher in `_stream`.
- **Sperre:** Läuft schon ein Ablauf, wirft `start()` `OperationBusy` mit Art und Modul des laufenden Ablaufs.
  Die Sperre wird erst frei, wenn der Thread fertig ist, nicht schon beim Verbindungsende.
- `follow(op)` ist der Iterator für den Stream. Er liefert bereits vorhandene und neue Zeilen und endet mit
  `done` bzw. `error`. Bricht der Leser ab, passiert dem Thread nichts.

`api/routes/modules.py`:
- `_stream(kind, module_id, gen)` ruft `operations.start(...)` auf und streamt `operations.follow(op)` im
  **bisherigen Format** (`{"line"}`, `{"done": true}`, `{"error"}`).
- Bei `OperationBusy` wird **409** mit `coded(409, "module_operation_busy", module=…)` zurückgegeben.

`frontend/src/features/modules/api.ts`:
- Ist die Antwort nicht ok, liest `stream()` den JSON-Inhalt und zeigt `buildErrorMessage(...)` an (wie
  `api-client`). Damit steht dort „Gerade läuft schon eine Modul-Änderung (…). Bitte kurz warten.“ statt
  „HTTP 409“. Text in `errors` (de/en), ohne Terminal-Hinweis.

Unverändert bleiben: `installer.install/update/uninstall` (Reihenfolge, Neustart-Verzögerung 2 s), das Format des
Streams, `ModuleCard`/`ModuleCockpitCard` und „Alle updaten“. Letzteres startet die Module nacheinander und
wartet auf `done`, deshalb gibt es dort keine 409.

**Nicht in diesem Schritt:** Fortschritt nach dem Neuladen der Seite wieder anzeigen. Nach dem Neustart zeigt die
Karte ohnehin die neue Version. Eine Statusroute wäre eine eigene Etappe, falls Till das möchte.

## Tests (TDD)

`core/tests/test_module_operations.py`:
1. Der Ablauf läuft zu Ende, auch wenn der Leser nach der ersten Zeile aufhört. Der letzte Schritt (Attrappe für
   „Neustart angefordert“) wird erreicht.
2. Ein Fehler im Generator ergibt `error` im Stream und ein Log, und die Sperre wird wieder frei.
3. Ein zweiter Start während eines laufenden Ablaufs ergibt `OperationBusy`. Nach dem Ende ist ein neuer Start
   möglich.
4. `follow` liefert alle Zeilen in der richtigen Reihenfolge, auch wenn der Leser erst später kommt.

`core/tests/test_modules_routes.py`:
5. Das Stream-Format bleibt gleich (`line` …, `done`).
6. 409 `module_operation_busy`, wenn schon ein Ablauf läuft.
7. Route schon während des Ablaufs verlassen (Leser bricht ab): Der Installer-Generator läuft trotzdem bis zum Ende.

Gegenprobe auf `main`: 1, 3, 6 und 7 müssen dort rot sein.

## Prüfung

- Volle Suite, ruff, `tsc -b`, eslint, vitest (`api.ts`: 409 zeigt den übersetzten Text), Mutanten.
- hydratest:
  - `curl -m 2` gegen das `example`-Update: Danach muss es einen Neustart geben (`ActiveEnterTimestamp`
    ändert sich), und die Version ist neu.
  - Browser-Skript mit Abbruch nach 1,5 s.
  - Zweiter Klick während eines laufenden Updates ergibt eine Meldung statt eines doppelten Builds.
- Frischer 26.04-Container ist nicht nötig, weil Installer und Start nicht betroffen sind. Es ändert sich nur der
  Ablauf im laufenden Dienst.
