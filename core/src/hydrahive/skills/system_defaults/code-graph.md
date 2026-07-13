---
name: code-graph
description: Den Code-Graph des Projekts abfragen statt den Quellcode zu durchwühlen
when_to_use: Wenn du verstehen willst wie Code zusammenhängt — was ruft was auf, was hängt an einem Symbol, was bricht bei einer Änderung, wie hängen zwei Dateien zusammen. Bevor du dich mit grep durch viele Dateien liest.
tools_required: [graph_query, graph_explain, graph_path, graph_affected, graph_refresh]
---

# Code-Graph nutzen statt Grep-und-Lesen

Das aktive Projekt kann einen **Code-Graph** haben (im Cockpit unter „Code-Graph"
gebaut) — einen Abhängigkeitsgraphen aus AST-Analyse. Ihn abzufragen ist oft
schneller und token-günstiger als den Quellcode zu durchsuchen.

## Wann den Graph, wann Grep

**Graph zuerst** bei Struktur-/Zusammenhang-Fragen:
- „Was hängt an `require_auth`?" → `graph_query`
- „Wie hängen `mcp.py` und `errors.py` zusammen?" → `graph_path`
- „Was bricht, wenn ich `db()` ändere?" → `graph_affected`
- „Was macht `TriggerEvent` und womit ist es verbunden?" → `graph_explain`

**Grep/Read** bleibt richtig für:
- konkreten Code lesen/ändern (der Graph liefert Datei:Zeile — dann gezielt lesen)
- Textsuche nach Strings/Konstanten
- wenn kein Graph existiert

## Ablauf

1. **`graph_query "<frage>"`** — natürlichsprachige Frage, BFS-Traversal. Liefert
   relevante Knoten mit `datei:zeile`. `budget` begrenzt die Antwortgröße.
2. Aus dem Ergebnis die **relevanten Dateien:Zeilen** nehmen und gezielt mit
   `file_read` öffnen — statt blind viele Dateien zu grep-en.
3. Für „Impact einer Änderung": **`graph_affected "<symbol>"`** vor dem Umbau.
4. Für „wie erreicht A B": **`graph_path "A" "B"`**.

## Graph aktualisieren nach eigenen Änderungen

Der Graph ist so aktuell wie sein letzter Build. Hast du selbst Code geändert
(neue Datei, umbenannt, größeres Refactoring) und willst danach wieder
zuverlässig `graph_query`/`graph_affected` nutzen, baue ihn neu:

- **`graph_refresh`** — baut den Graph lokal neu (ohne LLM/Kosten) über die im
  Cockpit gewählten Verzeichnisse. Dauert Sekunden bis ~1-2 Minuten. Danach
  spiegeln die Abfragen den aktuellen Code.

Wann sinnvoll:
- Vor einer Impact-Analyse (`graph_affected`), wenn du seit dem letzten Build
  schon Dateien angefasst hast — sonst basiert die Analyse auf altem Stand.
- Nach dem Abschluss eines Features/Refactors, bevor du den Graph erneut befragst.

Nicht bei jeder Kleinigkeit neu bauen — nur wenn die Struktur sich geändert hat
und du dich danach wieder auf den Graph stützen willst.

## Wenn kein Graph da ist

Die Abfrage-Tools antworten dann mit einem Hinweis „erst im Cockpit den Graph
bauen". Das ist kein Fehler — dann normal mit `grep`/`file_read` weiterarbeiten
und dem User ggf. vorschlagen, den Code-Graph im Cockpit zu bauen. `graph_refresh`
funktioniert erst, wenn im Cockpit einmal Scan-Verzeichnisse gewählt wurden.

## Merke
- Der Graph zeigt **Struktur**, nicht den aktuellen Datei-Inhalt Zeile für Zeile.
  Immer die genannten Stellen danach mit `file_read` verifizieren, bevor du
  Änderungen darauf stützt.
- Nach größeren Refactors mit `graph_refresh` neu bauen, sonst ist er veraltet.
