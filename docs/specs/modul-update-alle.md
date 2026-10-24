# „Alle updaten“ bei Modulen: ein Ablauf, einmal bauen, einmal neu starten

Task b74c972d. Meldung von Till am 24.10.2026: „Alle updaten“ geht nicht, man muss jedes Modul einzeln
aktualisieren. Gilt vor dem Merge von hydrahive2-modules#261 (29 Updates auf einmal).

## Problem (nachgestellt auf hydratest am 24.10.)

„Alle updaten“ (`ModulesOverlay.tsx`, `ModulesPage.tsx`) startet die Einzel-Updates nacheinander. Jedes
`installer.update()` endet mit `_frontend_build()` (etwa 23 s) und `_request_restart()`. Der Neustart kommt 2 s
später über `.restart_request`, der Timer prüft alle 5 s. Er fällt mitten in das nächste Update.

Ablauf im Protokoll, 4 offene Updates:

| Zeit | Ereignis |
|---|---|
| 13:47:08 | boardgames ersetzt, Build, Neustart angefordert |
| 13:47:31 | minigames startet noch im alten Prozess |
| 13:47:35 | Dienst startet neu, mitten in minigames |
| 13:47:55 | notizbuch: `POST` ergibt **502** (Dienst startet gerade). Die Schleife wertet Fehler wie „fertig“ und hört auf. |

Ergebnis: 2 von 4 Updates liefen durch. Selbst wenn alles klappte, kosten 29 Updates 29 Builds und 29 Neustarts,
also rund 30 Minuten.

## Ziel

- Ein Klick aktualisiert **alle** Module mit verfügbarem Update in **einem** Ablauf: alle Dateien ersetzen,
  **einmal** bauen, **einmal** neu starten.
- Scheitert ein Modul (z. B. fehlende Rechte), laufen die anderen weiter. Am Ende steht klar da, welche
  geklappt haben und welche nicht, mit Grund.
- Der Ablauf läuft wie die Einzel-Updates im Hintergrund zu Ende, auch ohne offenen Browser
  (`operations.start`). Es läuft höchstens ein Modul-Ablauf gleichzeitig (409 `module_operation_busy`).
- Das Einzel-Update bleibt unverändert.

## Lösung

### Backend

`installer.update_all() -> Iterator[str]` (neue Datei `modules/update_all.py`, damit `installer.py` unter etwa
200 Zeilen Zuwachs bleibt; Aufruf über `installer`):

1. `refresh()` einmal. Danach die Liste aller installierten Module mit `is_update_available(installiert, Hub)`,
   alphabetisch.
2. Nichts zu tun: Zeile „Alle Module sind aktuell“, kein Build, kein Neustart.
3. Je Modul, in einem eigenen `try`:
   - Abhängigkeiten sicherstellen (`_ensure_dependencies`).
   - Dienst stoppen, falls vorhanden.
   - `replace_module_in(id)` und Dienst starten, falls vorhanden.
   - Zeilen: `[modules] update <id> …`, dann `… <id>: fertig (<alt> → <neu>)` bzw. `… <id>: FEHLER – <Grund>`.
   - Ein Fehler (`InstallError`, `OSError`, `subprocess.CalledProcessError`) wird geloggt, gezählt und
     übersprungen.
4. Mindestens ein Modul ersetzt: **einmal** `_frontend_build()`, dann **einmal** `_request_restart()`.
   Schlägt der Build fehl, ist das ein Fehler des ganzen Ablaufs (Stream `error`). Es gibt dann keinen
   Neustart, damit kein halbes Frontend ausgeliefert wird.
5. Schlusszeile: `[modules] Fertig: <n> aktualisiert, <m> fehlgeschlagen` und bei Fehlern
   `[modules] Fehlgeschlagen: a (Grund), b (Grund)`.
   Alle gescheitert: Stream `error` mit Code `module_update_all_failed` und der Liste.

Route `POST /api/admin/modules/update-all` (Admin, SSE wie die anderen, `kind="update-all"`,
`module_id="*"`). Sie muss **vor** `/{module_id}/update` registriert sein, damit `update-all` nicht als Modul-ID
gilt.

### Frontend

- `modules/api.ts`: `updateAllModules(onLine, onDone, onError)`, der Stream ist `POST /update-all`.
- `ModulesOverlay.tsx` und `ModulesPage.tsx`: Der Knopf „Alle updaten“ ruft `updateAllModules` auf, statt eine
  Schleife zu fahren.
  - Fortschritt: Zähler aus den Zeilen „fertig“ bzw. „FEHLER“ (`done/total`), danach „Wird gebaut …“ und
    „Neustart …“.
  - Am Ende eine Zusammenfassung, bei Fehlern die betroffenen Module mit Grund (rot), sonst „Alle aktualisiert“.
- Die reine Logik steckt in `features/modules/updateAllProgress.ts` (Zeilen → Fortschritt und Zusammenfassung),
  getestet.
- Texte de/en unter `modules:update.*`, Fehlercode `module_update_all_failed` unter `errors`.

## Tests (TDD)

Backend (`core/tests/test_module_update_all.py`):
1. Drei Module mit Update: alle drei ersetzt, **genau ein** Build und **ein** Neustart, in dieser Reihenfolge
   nach dem letzten Ersetzen.
2. Ein Modul wirft `PermissionError`: Die anderen werden trotzdem ersetzt, einmal Build und Neustart, die
   Schlusszeile nennt das Modul mit Grund.
3. Nichts zu tun: kein Ersetzen, kein Build, kein Neustart.
4. Alle scheitern: kein Build, kein Neustart, Fehler `module_update_all_failed`.
5. Build scheitert: kein Neustart, Fehler im Ablauf.
6. Nur Module mit `update_available`, nicht installierte bleiben unberührt. Dienst-Module werden gestoppt und
   gestartet.
7. Route: `POST /api/admin/modules/update-all` streamt im üblichen Format, nur Admin (401/403), 409 bei
   laufendem Ablauf. `update-all` wird nicht als Modul-ID behandelt.

Frontend: `updateAllProgress.test.ts` (Zähler, Phase, Zusammenfassung). Der Knopf ruft `updateAllModules` statt der
Schleife auf (`ModulesOverlay`).

Gegenprobe: Die neuen Tests sind auf `main` rot.

## Prüfung

- Volle Testreihe, ruff, `tsc -b`, eslint, vitest, Mutanten.
- hydratest: 4 offene Updates herstellen (wie oben). Ein Klick auf „Alle updaten“ ergibt alle gesunden Module
  aktualisiert, einen Build, einen Neustart, und der Archiver steht mit Grund in der Liste.
- Danach mit dem Modul-Zweig aus #261: 29 Updates mit einem Klick.

## Nicht enthalten

- Rechte des Archiver-Ordners auf hydratest (Zustand des Testservers, kein Code-Fehler).
- Fortschritt nach dem Neuladen der Seite wieder anzeigen.

## Nachtrag: verständlicher Grund

Beim echten Test auf hydratest stand im Ergebnis der rohe Systemfehler, z. B.
„archiver – [Errno 13] Permission denied: '/var/lib/hydrahive2/modules/archiver' -> '…/previous'“.
Für Laien ist das unverständlich.

- Die Zeile `… <id>: FEHLER – <Grund>` enthält einen **kurzen Grund in einfacher Sprache**:
  - `PermissionError`: „keine Schreibrechte auf den Modul-Ordner“
  - anderer `OSError`: „Dateifehler beim Ersetzen“
  - `CalledProcessError`: „Dienst des Moduls ließ sich nicht stoppen oder starten“
  - `InstallError`: dessen Text (Code, z. B. `module_not_in_hub:<id>`)
- Der vollständige Fehler mit Pfad steht weiter im Server-Protokoll (`logger.exception`).
- Die Ergebnisbox zeigt unter der Liste den Hinweis: „Einzelne Module erneut über ihren Knopf ‚Aktualisieren'
  versuchen. Bleibt es dabei, sieht ein Admin im Server-Protokoll den genauen Grund.“
