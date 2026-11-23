# Websuche – damit deine Agenten im Internet nachschlagen können

Mit der Websuche können Buddy und deine Agenten im Internet nach aktuellen Informationen suchen. Die Suche läuft über
eine eigene SearXNG-Suchmaschine auf deinem Server. Wenn du möchtest, springt der Dienst Tavily ein, falls SearXNG
ausfällt oder zu wenig findet.

## So startest du

1. SearXNG installieren: Öffne **Admin** → **Extensions** und installiere die Karte **SearXNG (Metasuchmaschine)** mit
   **Installieren** → **Installation starten**.
2. Adresse nachschauen: Nach der Installation steht die Adresse unter **Admin** → **Credentials** im Reiter
   **Extensions** beim Eintrag **SearXNG (Metasuchmaschine)** (Feld **URL**).
3. Adresse eintragen: Öffne **Admin** → **Betriebszentrale** → **Globale Einstellungen**, Reiter **Websuche**, und trage
   die Adresse bei **SearXNG-URL** ein. Gespeichert wird, sobald du das Feld verlässt. Ein Häkchen zeigt, dass es
   geklappt hat.
4. Prüfen: Auf dem Dashboard zeigt der Bereich **System-Status** den Punkt **Websuche**. Grün heißt: Die Suche liefert
   Ergebnisse.
5. Ausprobieren: Bitte Buddy zum Beispiel „Such im Web nach den neuesten Nachrichten zu …“.

Die Einstellungen können nur Admins ändern. Ohne eingetragene **SearXNG-URL** gibt es keine Websuche, auch nicht über
Tavily.

## Was du damit machen kannst

### Einstellungen im Reiter **Websuche**
Im Reiter **Websuche** unter **Globale Einstellungen** gibt es zwei Felder:
- **SearXNG-URL**: die Adresse deiner SearXNG-Suchmaschine. Pflicht für die Websuche.
- **Tavily API-Key**: optional. Den Schlüssel bekommst du kostenlos bei Tavily (app.tavily.com), ohne Kreditkarte. Ein
  eingetragener Schlüssel wird nicht mehr angezeigt, im Feld steht dann nur „(gesetzt)“.

Die Markierung **GUI** neben einem Feld zeigt: Dieser Wert wurde hier in der Oberfläche gesetzt. Beide Werte liest die
Websuche bei jeder Suche neu, ein Neustart ist nicht nötig.

### Suchen wie im Netz
Der Agent bekommt eine Trefferliste mit Titel, Adresse, kurzem Textauszug und der Quelle (welcher Suchanbieter den
Treffer geliefert hat). Wenn bekannt, steht auch das Datum dabei. SearXNG sucht auf Deutsch. Standardmäßig kommen bis
zu 10 Treffer, auf Wunsch bis zu 50. Treffer ohne brauchbare Internetadresse sortiert HydraHive aus.

### Nachrichten und Zeitraum
Für Aktuelles kann der Agent gezielt in Nachrichten suchen und den Zeitraum eingrenzen: letzter Tag, letzte Woche,
letzter Monat oder letztes Jahr. Findet eine normale Suche mit Zeitraum nichts, versucht HydraHive es einmal
automatisch in den Nachrichten.

### Tavily als Ersatz und Ergänzung
Ist ein **Tavily API-Key** eingetragen, hilft Tavily in zwei Fällen:
- Ersatz: SearXNG ist nicht erreichbar oder antwortet fehlerhaft, oder alle gefragten Suchanbieter sperren und es
  gibt keine Treffer. Dann sucht Tavily statt SearXNG.
- Ergänzung: Eine normale Suche (keine Nachrichtensuche) bringt weniger als 3 Treffer. Dann ergänzt Tavily die
  Liste um weitere Treffer, ohne doppelte Adressen.

Ohne Schlüssel wird Tavily nie gefragt.

### Treffer im Chat
Im Chat erscheint die Suche als Karte mit der Überschrift `web_search`, dem Suchbegriff und der Anzahl der Treffer.
Jeder Treffer ist anklickbar und öffnet sich in einem neuen Tab. Gab es nichts, steht dort **Keine Treffer.**

### Zustand im Dashboard
Der Punkt **Websuche** im **System-Status** schickt beim Laden des Dashboards und danach alle 30 Sekunden eine echte
Probesuche an SearXNG:
- grau: keine **SearXNG-URL** eingetragen,
- grün: Die Suche liefert Ergebnisse. Fallen einzelne Anbieter aus, steht das im Hinweis beim Darüberfahren
  („ausgefallen: …“),
- gelb: eingetragen, aber nicht erreichbar, keine Antwort im richtigen Format oder keine Ergebnisse (zum Beispiel
  „keine Ergebnisse — gesperrt: …“).

Ein Klick auf den Punkt öffnet die Systemseite. Tavily wird dabei nicht geprüft.

## Mit Buddy und Agenten

Das Werkzeug heißt `web_search`.
- Buddy hat die Websuche von Anfang an.
- Projekt-Agenten und Spezialisten bekommen sie nicht automatisch. Schalte sie in den Einstellungen des Agenten im
  Reiter **Tools & MCP** frei. Beim Projekt-Agenten im Projekt heißt der Reiter **Tools**. Mit dem Filter **Web**
  findest du das Werkzeug schneller.

Was du fragen kannst:
- „Such im Web nach …“
- „Was gibt es heute Neues zu …?“ (Nachrichten, Zeitraum Tag)
- „Welche Artikel zu … sind diesen Monat erschienen?“

Was nicht geht:
- Die Websuche liefert nur Trefferlisten mit kurzen Auszügen, keine ganzen Seiten.
- Über Tavily kommen höchstens 20 Treffer pro Suche.
- Andere Arten als normale Suche und Nachrichten gibt es nicht.

## Gut zu wissen

### Grenze von Tavily
Der kostenlose Tavily-Zugang erlaubt 1.000 Suchen im Monat. HydraHive zählt selbst mit und hört bei 950 Aufrufen im
Kalendermonat auf, damit das Gratis-Kontingent nie überschritten wird. Gezählt wird jeder Aufruf, auch einer, der
danach fehlschlägt. Ist die Grenze erreicht, gilt:
- Als Ersatz: Die Suche meldet „Tavily-Monatskontingent fast aufgebraucht (950 Aufrufe) – Ersatz pausiert bis
  Monatsende.“
- Als Ergänzung: Der Agent bekommt nur die Treffer von SearXNG.

Im neuen Monat beginnt die Zählung von vorn.

### Datenschutz
Deine Suchanfragen gehen an deine eigene SearXNG-Suchmaschine, die die öffentlichen Suchanbieter fragt. Springt Tavily
ein, geht die Suchanfrage an Tavily. Der Tavily-Schlüssel steht nie in Fehlermeldungen und wird nur bei der Anfrage an
Tavily mitgeschickt.

### Typische Fehlermeldungen
Der Agent gibt diese Meldungen weiter, wenn die Suche nicht klappt:
- „SearxNG nicht konfiguriert — URL in den Einstellungen hinterlegen“: Die **SearXNG-URL** fehlt.
- „SearxNG-Request fehlgeschlagen: …“: SearXNG ist nicht erreichbar, die Adresse stimmt nicht, oder SearXNG lehnt die
  Anfrage ab. HydraHive braucht Antworten im JSON-Format. Die Installation über **Extensions** schaltet das ein; bei
  einer selbst eingerichteten SearXNG-Suchmaschine musst du das JSON-Format selbst erlauben.
- „SearxNG-Antwort kein JSON“: Unter der Adresse antwortet etwas, aber nicht im erwarteten Format. Adresse prüfen.
- „Websuche liefert keine Treffer — Suchanbieter gesperrt: … Dienst prüfen (SearXNG).“: Alle Suchanbieter haben
  gesperrt (zum Beispiel wegen CAPTCHA), und es ist kein **Tavily API-Key** eingetragen.
- „… Ersatz fehlgeschlagen: Tavily: HTTP …“ oder „… Ersatz fehlgeschlagen: Tavily nicht erreichbar (…)“: Tavily ist
  eingesprungen, hat aber nicht geantwortet. Prüfe den Schlüssel.

Keine Treffer ohne Fehlermeldung bedeuten: Die Suche hat funktioniert, aber nichts gefunden.

*Stand: HydraHive 2.0.0, 23.11.2026*
