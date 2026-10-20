# Websuche verbessern – kostenlos

Stand: 20.10.2026 · Task 611259b2 · Vorgänger: `websearch-blocked-engines.md` (02.10.)

## 1. Anlass

Am 20.10. hat Till den AfD-Mail-Leak (Borncity, Spiegel, FAZ vom selben Tag) gesucht. `web_search` hat
nichts Aktuelles gefunden: oben standen afd.de und Wikipedia, dazu ein Morgenpost-Artikel von 2017.
Brave meldete „zu viele Anfragen“, DuckDuckGo und Startpage ein CAPTCHA.

Till hat festgelegt: **nur kostenlose Wege**, keine laufenden API-Kosten.

## 2. Befund (gemessen am 20.10. auf .2, SearXNG `127.0.0.1:8888`, Kern `origin/main` 6063a156)

### 2.1 SearXNG kann mehr, als `web_search` abfragt

Anfrage „AfD Leak E-Mails“, `language=de`:

| Aufruf                                        | Treffer | Inhalt                                          |
|-----------------------------------------------|--------:|-------------------------------------------------|
| so wie `web_search` heute fragt (nur `q`)     | 24      | afd.de, Wikipedia, dawum – nichts zum Leak      |
| `categories=news`                             | 31      | FAZ, taz, Borncity, winfuture, Spiegel …        |
| `categories=news&time_range=week`             | 10      | nur aktuelle Artikel zum Leak                   |
| `categories=general&time_range=week`          | 0       | alle allgemeinen Anbieter gesperrt              |

`web_search` sendet nur `q`, `format`, `language`. **Kategorie und Zeitraum kann der Agent heute nicht
wählen.** `publishedDate` und `engine` jedes Treffers werden verworfen, deshalb kann der Agent einen
Artikel von 2017 nicht als alt erkennen.

### 2.2 Einzelne Anbieter (`engines=<name>`)

| Anbieter          | Ergebnis                         |
|-------------------|----------------------------------|
| bing              | 10 Treffer                       |
| yandex            | 15 Treffer                       |
| bing news         | liefert (Hauptquelle in 2.1)     |
| duckduckgo news   | **28 Treffer** (FAZ …)           |
| qwant, qwant news | „Zugriff verweigert“             |
| presearch (+news) | HTTP-Fehler                      |
| mojeek (+news), tagesschau, wikinews, reuters | 0 Treffer, kein Fehler |
| google, google news | leer bzw. CAPTCHA              |
| brave, duckduckgo, startpage | gesperrt (wie am 02.10.) |

→ **Kein weiterer Gratis-Anbieter bringt heute etwas.** Bing News und DuckDuckGo News sind schon an.
Die SearXNG-Konfiguration bleibt deshalb unverändert (Teil C ist damit geprüft und erledigt).

### 2.3 `fetch_url`

- Kein eigener User-Agent: httpx schickt `python-httpx/x.y`, das blocken manche Seiten.
- Die Antwort ist rohes HTML samt CSS und JS, gekappt bei `_MAX_BYTES = 200_000`. Beim Borncity-Artikel
  kamen so rund **190.000 Zeichen** an, davon war der Artikel nur ein kleiner Teil. Das kostet unnötig Token.
- Im Kern-venv gibt es keine Bibliothek für Textextraktion (trafilatura, readability, bs4, lxml fehlen).
- JS-Seiten deckt `web_browser` schon ab (Playwright steckt im Kern). **Kein** eigenes Rendering in `fetch_url`.

### 2.4 Tavily (Quelle: docs.tavily.com, abgerufen 20.10.)

- Plan „Researcher“: **1.000 Credits pro Monat kostenlos, ohne Kreditkarte**.
- Basic-Suche kostet 1 Credit, Advanced 2.
- Development-Key: 100 Anfragen pro Minute.
- Parameter `topic` (`general`/`news`), `time_range`, `max_results`. Datum der Treffer bei `topic=news`.
- Pay-as-you-go ($0.008 pro Credit) gibt es nur, wenn man es aktiv einschaltet. Ohne Karte kann nichts
  abgebucht werden.

## 3. Ziel

1. Der Agent findet aktuelle Nachrichten, ohne dass jemand die URL hinschreiben muss.
2. Er sieht, wie alt ein Treffer ist und woher er kommt.
3. Fallen die SearXNG-Anbieter aus, gibt es einen kostenlosen zweiten Weg (Tavily).
4. `fetch_url` liefert auf Wunsch nur den lesbaren Text, das spart Token.
5. Nichts davon kostet Geld, und nichts Bestehendes ändert sich ohne neue Parameter.

## 4. `web_search` – Kategorie, Zeitraum, Datum

Neue optionale Parameter:

| Parameter    | Werte                                     | Standard    |
|--------------|-------------------------------------------|-------------|
| `category`   | `general`, `news`                         | `general`   |
| `time_range` | `day`, `week`, `month`, `year`            | ohne Filter |

- Sie werden 1:1 als `categories` und `time_range` an SearXNG gegeben. Andere Werte führen zu einem klaren Fehler.
- Jeder Treffer bekommt zusätzlich `published` (ISO-Datum, falls SearXNG eins liefert, sonst fehlt das
  Feld) und `source` (Name des Anbieters).
- **Automatischer Wechsel:** Kommen bei `category=general` mit gesetztem `time_range` 0 Treffer, wird
  **einmal** mit `category=news` nachgefragt. Die Antwort sagt das offen (`"fallback": "news"`).
  Begründung: Die Messung in 2.1 zeigt genau diesen Fall.
- Die Beschreibung des Werkzeugs sagt dem Agenten: „Für aktuelle Ereignisse `category=news` und
  `time_range` nutzen.“

## 5. Tavily als zweiter Weg

### 5.1 Wann

Tavily wird **nur** gefragt, wenn
- SearXNG nicht erreichbar ist oder einen Fehler liefert, **oder**
- SearXNG 0 Treffer liefert und Anbieter in `unresponsive_engines` stehen (also eine Sperre, nicht
  „gibt es nicht“),

**und** ein Tavily-Schlüssel eingetragen ist. Ohne Schlüssel bleibt alles wie heute.

So bleiben die 1.000 Credits für den Notfall. Der Agent kann Tavily nicht gezielt anwählen. Das ist
Absicht, damit die Credits nicht für Routinesuchen draufgehen.

### 5.2 Aufruf

- `POST https://api.tavily.com/search`, `search_depth: "basic"` (1 Credit), `topic` aus `category`,
  `time_range` durchgereicht, `max_results` = `count` (höchstens 20).
- `include_answer`, `include_raw_content` und `include_images` bleiben aus, damit der Aufruf bei 1 Credit bleibt.
- Treffer werden auf dasselbe Format gebracht: `title`, `url`, `snippet` (aus `content`), `published`
  (aus `published_date`), `source: "tavily"`. Die Antwort trägt `"provider": "tavily"`.

### 5.3 Schlüssel und Monatszähler

- Neue Einstellung `tavily_api_key` (`HH_TAVILY_API_KEY`, Typ `secret`, Gruppe „Websuche“) in
  `settings/editable.py`, wie der CoinGecko-Schlüssel. Hilfetext: „Kostenlos, 1.000 Suchen pro Monat.
  Nur als Ersatz, wenn SearXNG keine Treffer liefert.“
- Der Schlüssel wird nur serverseitig gelesen. Er erscheint nie im Ergebnis und nie im Log.
- **Monatszähler** in `data_dir/websearch/tavily_usage.json` (`{"month": "2026-10", "count": n}`):
  - Bei Monatswechsel geht er auf 0 zurück.
  - **Ab 950 im Monat** wird Tavily nicht mehr gefragt. Die Antwort sagt
    „Tavily-Monatskontingent fast aufgebraucht“.
  - Begründung: Fehlversuche und Zählfehler sollen das Gratis-Kontingent nie überschreiten, auch wenn ohne
    Karte keine Kosten entstehen könnten.
- Tavily-Fehler (401, 429, 432 „Plan-Limit“, Zeitüberschreitung) werden als kurze Meldung ohne
  Schlüssel und ohne Antwortkörper zurückgegeben. Der SearXNG-Befund bleibt dabei sichtbar.

## 6. `fetch_url` – Browser-Kennung und Text-Modus

### 6.1 Standard-Header

Fehlen sie in `headers`, setzt `fetch_url` sie selbst:
- `User-Agent`: aktueller Chrome-Desktop-String, als Konstante wie in `streaming/scraper.py`.
- `Accept`: `text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8`
- `Accept-Language`: `de-DE,de;q=0.9,en;q=0.8`

Header des Aufrufers haben immer Vorrang. Die Auth-Injection bleibt unverändert, ebenso der
SSRF-Schutz (DNS-Pinning, interne Adressen).

### 6.2 Neuer Parameter `format`

| Wert   | Wirkung                                                              |
|--------|----------------------------------------------------------------------|
| `raw`  | **Standard**, wie heute (Body unverändert)                           |
| `text` | nur lesbarer Text der Seite, plus `title` und `published`, falls vorhanden |

- `text` greift nur bei `content-type` HTML. Bei JSON, Text und anderem bleibt der Body roh, mit Hinweis
  `"format_applied": "raw"`.
- Extraktion **ohne neue Abhängigkeit**, mit `html.parser` aus der Standardbibliothek in einem neuen
  `tools/_html_text.py`:
  - Verworfen werden `script`, `style`, `noscript`, `svg`, `template`, `iframe`, `nav`, `footer`, `header`, `aside`, `form`.
  - Gibt es `<article>`, wird nur dessen Inhalt genommen, sonst `<main>`, sonst `<body>`.
  - Blockelemente (`p`, `h1`–`h6`, `li`, `br`, `div`, `tr`) werden zu Zeilenumbrüchen, Überschriften
    bekommen `#`-Präfixe, Links bleiben als Text (ohne URL).
  - Leerraum wird zusammengefasst und Entities aufgelöst.
  - `title` kommt aus `og:title` oder `<title>`, `published` aus `article:published_time` oder `<time datetime>`.
  - Text-Ergebnis höchstens 50.000 Zeichen, mit `truncated`. Gelesen werden höchstens 2 MB HTML
    (statt 200 KB), weil vom Rest nur ein Bruchteil übrig bleibt. Im `raw`-Modus bleibt die Grenze bei 200 KB.
- Entfernt der Text-Modus offensichtlich zu viel (weniger als 200 Zeichen), sagt die Antwort
  `"hint": "Seite braucht vermutlich JavaScript – web_browser nutzen"`.

Warum keine Bibliothek wie trafilatura: Sie würde lxml und weitere Pakete mitbringen, für alle
Installationen inklusive Mac-Test. Die Standardbibliothek reicht für Artikelseiten. Reicht sie
nachweislich nicht, ist trafilatura ein eigener Folgeschritt.

## 7. Nicht im Umfang

- Bezahl-APIs (Brave Search API, Serper, Bing API).
- Eigenes JS-Rendering in `fetch_url` (dafür gibt es `web_browser`).
- Änderungen an der SearXNG-Konfiguration (siehe 2.2).
- Ein Tavily-Werkzeug für Extract, Crawl oder Research.

## 8. Akzeptanzkriterien

1. `web_search(query, category="news", time_range="week")` liefert auf .2 zu „AfD Leak E-Mails“ aktuelle
   Artikel. Jeder Treffer hat `source`, `published` nur wenn vorhanden.
2. `web_search` ohne neue Parameter: Anfrage an SearXNG und Ergebnisform sind byte-gleich zu heute, bis
   auf die neuen Felder `source` und `published`.
3. Ungültige `category` oder `time_range` → `ToolResult.fail` mit verständlicher Meldung, kein Aufruf.
4. General + `time_range` mit 0 Treffern → genau ein zweiter Aufruf mit `news`, `"fallback": "news"` in der Antwort.
5. Ohne Tavily-Schlüssel wird Tavily nie aufgerufen (Test: kein HTTP-Aufruf an api.tavily.com).
6. Mit Schlüssel: Tavily nur bei Fehler, oder bei 0 Treffern mit gesperrten Anbietern. Bei Treffern von
   SearXNG kein Tavily-Aufruf.
7. Zähler: Jeder Tavily-Aufruf zählt +1, Monatswechsel setzt auf 0 zurück, ab 950 kein Aufruf mehr.
   Die Datei wird atomar geschrieben.
8. Schlüssel taucht in keinem Ergebnis, keiner Fehlermeldung und keinem Log auf (Test mit Fehlerantwort,
   die den Schlüssel enthält).
9. `fetch_url` setzt UA, Accept und Accept-Language nur, wenn der Aufrufer sie nicht gesetzt hat. Auth und
   SSRF-Tests bleiben grün.
10. `fetch_url(format="text")`:
    - Auf einer Borncity-ähnlichen Fixture enthält der Text Überschrift und Absätze des Artikels, aber
      kein CSS, kein JS und keine Navigation.
    - `title` und `published` sind gesetzt, der Text ist weniger als 10 % des HTML.
11. `format="text"` auf JSON → Body roh, `"format_applied": "raw"`.
12. Mutanten-Gegenprobe auf Fallback-Bedingung, Zähler-Grenze, Header-Vorrang und Script-Entfernung.

## 9. Dateien

| Datei                                         | Änderung                                       |
|-----------------------------------------------|------------------------------------------------|
| `core/src/hydrahive/tools/web_search.py`      | Parameter, Felder, News-Fallback, Tavily-Aufruf |
| `core/src/hydrahive/tools/_tavily.py`         | neu: Aufruf, Abbildung, Monatszähler            |
| `core/src/hydrahive/tools/fetch_url.py`       | Standard-Header, `format`                       |
| `core/src/hydrahive/tools/_html_text.py`      | neu: Textextraktion (stdlib)                    |
| `core/src/hydrahive/settings/editable.py`     | `tavily_api_key`                                |
| `core/tests/test_web_search_tool.py`          | erweitert                                       |
| `core/tests/test_tavily.py`, `test_html_text.py`, `test_fetch_url_format.py` | neu    |

Jede Datei bleibt unter ~200 Zeilen (`fetch_url.py` hat heute 193). Die Header-Logik und die Auswertung
von `format` kommen deshalb in `_html_text.py` bzw. einen kleinen Helfer, nicht in `fetch_url.py` selbst.

## 10. Nach dem Merge

- Till legt bei app.tavily.com einen kostenlosen Schlüssel an und trägt ihn unter Einstellungen → Websuche ein.
- Live-Abnahme auf .2: Suche aus 8.1 und ein `fetch_url(format="text")` auf den Borncity-Artikel. Den Tavily-Weg
  teste ich, indem ich SearXNG für einen Aufruf über die Tool-Config auf eine tote URL stelle.
