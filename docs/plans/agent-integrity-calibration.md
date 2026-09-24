# Plan: Agent Integrity — letzte Fehlalarm-Kalibrierung

## Live-Befund

- Die natürliche Fortsetzung „ok, machen wir das alles noch fertig und dann die agenten“ liegt außerhalb des absichtlich engen Continuation-Matchers.
- Alle fünf aktuell nach Tool aufgeschlüsselten `no_progress`-Signale stammen von `file_patch`. Unterschiedliche erfolgreiche Änderungen liefern denselben generischen Tool-Output und erhöhen dadurch fälschlich den Ergebnis-Streak.

## Änderungen

### Continuation

- [x] RED-Test mit der realen Nutzerformulierung.
- [x] Klare deutsche Abschlussformulierungen (`das/dies/alles … fertig`) mit optionalem Folgeschritt erkennen.
- [x] Neue konkrete Arbeitsaufträge und negierte Formulierungen weiterhin ablehnen.

### Fortschritt

- [x] RED-Test: drei unterschiedliche erfolgreiche `file_patch`-Aktionen erzeugen kein `no_progress`.
- [x] Erfolgreiche Aktionen mit klassifizierter Evidenz setzen den Ergebnis-No-Progress-Streak zurück.
- [x] Identische Aktionen bleiben über `repeated_tool_action` sichtbar.
- [x] Fehlerketten und wiederholte read-only Ergebnisse bleiben erkennbar.

### Abschluss

- [x] Continuity-, Integrity-, Runner-, Metrics-, Cache- und Auth-Tests ausführen.
- [x] Ruff, Compile, HH- und Security-Review ausführen.
- [x] Prompt-Zuwachs 0 bestätigen.
- [ ] PR, CI, Merge, Deployment und echten Live-Smoke abschließen.

## Grenzen

- Kein Enforcement.
- Keine Rohargumente oder Outputs in Metadaten/Metriken.
- Kein pauschales Matching jedes Satzes mit „fertig“.
- Keine Unterdrückung des separaten Signals für identische Toolaktionen.

## Vorab-Verifikation

- 98 fokussierte Integrity-, Continuity-, Runner-, Metrics-, Cache- und Auth-Tests bestanden.
- Reale Nutzerformulierung als Regressionstest übernommen.
- Unterschiedliche erfolgreiche Dateiänderungen erzeugen kein `no_progress`; identische Aktionen erzeugen weiterhin `repeated_tool_action`; wiederholte read-only Ergebnisse bleiben sichtbar.
- Ruff, Compile und Diff-Prüfung bestanden.
- Security-Review: Regex auf 120 Zeichen begrenzt, Negationen ausgeschlossen, keine neue Persistenz oder API-Ausgabe.
- HH-Review: keine Promptänderung, keine neue Kopplung, reine Runner-Kalibrierung.
