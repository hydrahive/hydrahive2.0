# Erste Schritte mit HydraHive

Willkommen! Diese Seite ist dein roter Faden. HydraHive ist groß — aber du musst
nicht alles auf einmal verstehen. Hier ist der kürzeste Weg von „gerade
eingeloggt" zu „es läuft".

## Was ist HydraHive überhaupt?

HydraHive ist eine Plattform, auf der **KI-Agenten** für dich arbeiten. Ein Agent
ist ein KI-Assistent mit einer Rolle, eigenen Werkzeugen und Zugriff auf das, was
du ihm erlaubst. Du kannst mit ihnen reden, ihnen Aufgaben geben, und sie
automatisiert Dinge im Hintergrund erledigen lassen.

Es gibt zwei Haupt-Arbeitsorte:

- **Buddy** (die Startseite 🫀) — dein **persönlicher Assistent** für den Alltag.
  Eine durchgehende Unterhaltung, immer für dich da.
- **Werkstatt** (💬) — für **gezieltes Arbeiten** mit spezialisierten Agenten in
  getrennten Sitzungen (z.B. ein Coding-Agent für ein Projekt).

## Schritt 1 — Ein KI-Modell einrichten (Pflicht!)

Ohne ein hinterlegtes Sprachmodell kann kein Agent denken. Das ist der
allererste Schritt.

1. Gehe zu **Einstellungen → LLM-Konfiguration** (Zahnrad oben).
2. Trage bei einem Anbieter deinen **API-Schlüssel** ein (z.B. Anthropic, OpenAI,
   OpenRouter — je nachdem, was du hast).
3. Wähle ein **Standard-Modell**.
4. Fertig — jetzt können Buddy und die Agenten antworten.

> Kommt später überall „kein Modell konfiguriert" oder es passiert nichts, fehlt
> meist genau dieser Schritt.

## Schritt 2 — Mit Buddy reden

1. Klick oben links auf **Buddy** (das Herz-Symbol, Startseite).
2. Tippe unten eine Nachricht, z.B. *„Was kannst du für mich tun?"* → **Enter**.
3. Die Antwort erscheint live. Buddy kann Werkzeuge benutzen (Web-Suche, Dateien …)
   — welche, stellst du über das Zahnrad bei Buddy ein.

Buddy ist der einfachste Einstieg. Alles Weitere baut darauf auf.

## Schritt 3 — Ein Projekt anlegen (wenn du an etwas Konkretem arbeitest)

Ein **Projekt** ist ein abgegrenzter Arbeitsbereich mit eigenem Datei-Ordner
(Workspace). Agenten, die in einem Projekt arbeiten, „sehen" nur dessen Dateien —
sauber getrennt von allem anderen.

1. **Einstellungen → Projekte → Neu**.
2. Namen vergeben, optional ein Git-Repo verknüpfen.
3. In **Buddy** oder der **Werkstatt** kannst du dann dieses Projekt als Kontext
   wählen — die Datei-Werkzeuge arbeiten ab dann in seinem Workspace.

## Schritt 4 — Eigene Agenten (wenn Buddy nicht reicht)

Brauchst du einen Spezialisten (z.B. „Code-Reviewer", „Recherche-Agent"), legst
du unter **Einstellungen → Agenten** einen eigenen an: Rolle, Modell, erlaubte
Werkzeuge. In der **Werkstatt** startest du dann Sitzungen mit ihm.

## Wo finde ich was?

Die Navigation links ist in Gruppen sortiert:

- **Überblick** — Dashboard (Systemzustand, Aktivität).
- **Arbeiten** — Buddy, Werkstatt, Agenten, Projekte, Kommunikation, Teamchat.
- **Automatisierung** — Butler (Automationen), Skills, MCP, Plugins.
- **Infrastruktur** — VMs, Container, Datamining, Gedächtnis u.a.
- **Einstellungen** (Zahnrad) — LLM, Credentials, Module, Benutzer, System.

Auf vielen Seiten findest du oben ein **? -Symbol** — das öffnet die Hilfe genau
zu dieser Seite. Nutze es großzügig.

## Häufige Stolpersteine für Neue

- **„Es antwortet nichts / lädt ewig"** → Schritt 1 prüfen: Modell + gültiger
  API-Schlüssel unter LLM-Konfiguration.
- **„Der Agent kann X nicht"** → Das Werkzeug ist nicht aktiviert. Beim Agenten
  bzw. bei Buddy unter **Werkzeuge** einschalten.
- **„Der Agent kommt nicht auf eine geschützte Seite"** → Zugang unter
  **Credentials** hinterlegen (mit passendem URL-Muster).
- **„Wo sind meine Dateien?"** → Im **Workspace** des jeweiligen Projekts.

## Empfohlene Reihenfolge zum Einlesen

1. **Buddy** — dein Assistent (Startseite)
2. **LLM-Konfiguration** — damit alles funktioniert
3. **Projekte** — wenn du an etwas Konkretem arbeitest
4. **Agenten** — für Spezialisten
5. **Werkstatt** — gezieltes Arbeiten
6. **Credentials** — sobald externe Zugänge nötig werden

Viel Erfolg — und keine Sorge, du musst nicht alles auf einmal können. Fang mit
Buddy an.
