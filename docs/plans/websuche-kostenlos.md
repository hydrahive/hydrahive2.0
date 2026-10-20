# Bauplan: Websuche kostenlos

Spec: `docs/specs/websuche-kostenlos.md` (#577) · Task 611259b2 · Till 20.10.: SearXNG + Tavily, keine Brave-API.

Reihenfolge: je Schritt erst rote Tests (eigener Commit), dann Code. Am Ende Mutanten-Gegenprobe.

## Schritt 1 – `web_search`: Kategorie, Zeitraum, Datum/Quelle, News-Wechsel (Spec §4)

Tests `core/tests/test_web_search_tool.py` (erweitert):
- Ohne neue Parameter gehen genau `q`, `format`, `language` an SearXNG (keine `categories`/`time_range`).
- `category="news"`, `time_range="week"` → `categories=news`, `time_range=week` in den Parametern.
- Ungültige `category` bzw. `time_range` → `fail`, **kein** HTTP-Aufruf.
- Treffer enthalten `source` (= `engine`). `published` gibt es nur, wenn `publishedDate` gesetzt ist, gekürzt auf das Datum.
- `general` + `time_range` + 0 Treffer → genau ein zweiter Aufruf mit `categories=news`, `fallback: "news"`.
- `general` **ohne** `time_range` + 0 Treffer → kein zweiter Aufruf.
- `news` + 0 Treffer → kein zweiter Aufruf.
- Die bestehenden 10 Tests bleiben unverändert grün.

Code: `web_search.py` bleibt unter 200 Zeilen. Abbildung der Treffer und Prüfung der Parameter kommen in `tools/_search_params.py`.

## Schritt 2 – Tavily als Ersatz (Spec §5)

Neu: `core/src/hydrahive/tools/_tavily.py`
- `async def search(query, *, topic, time_range, count, api_key) -> dict` (Aufruf + Abbildung)
- `reserve() -> bool`: Monatszähler in `settings.data_dir/websearch/tavily_usage.json`, Lock, atomar (tmp + `os.replace`).
  Zählt **vor** dem Aufruf, damit Fehlversuche mitzählen. Ab 950 gilt `False`.
- Einstellung `tavily_api_key` (secret, Gruppe „Websuche“) in `settings/editable.py`.

Tests `core/tests/test_tavily.py` (neu):
- Abbildung: `content`→`snippet`, `published_date`→`published`, `source: "tavily"`.
- Request-Körper: `search_depth: "basic"`, `topic`, `time_range` nur wenn gesetzt, `max_results` ≤ 20,
  keine Felder `include_answer`, `include_raw_content` oder `include_images`. Schlüssel steht im `Authorization`-Header.
- Zähler: +1 je Aufruf, Monatswechsel → 0, bei 950 `False`, kaputte Datei → wie leer.
- Fehler 401/429/432/Zeitüberschreitung → Meldung ohne Schlüssel und ohne Antwortkörper (Test: Body enthält den Schlüssel).

Tests in `test_web_search_tool.py`:
- Ohne Schlüssel: nie ein Tavily-Aufruf, auch nicht bei Sperre oder Fehler (Verhalten wie heute).
- Mit Schlüssel und SearXNG-Treffern → kein Tavily-Aufruf.
- Mit Schlüssel, 0 Treffern und gesperrten Anbietern → Tavily, `provider: "tavily"`, `unavailable` bleibt sichtbar.
- Mit Schlüssel und SearXNG-HTTP-Fehler → Tavily.
- Mit Schlüssel, 0 Treffern **ohne** Sperre → kein Tavily-Aufruf (es gibt wirklich nichts).
- Kontingent erschöpft → `fail`, im Text „Tavily-Monatskontingent“ und die SearXNG-Sperre.
- Tavily-Fehler → `fail` mit beiden Befunden, kein Schlüssel im Text.

## Schritt 3 – `fetch_url`: Standard-Header + `format=text` (Spec §6)

Neu: `core/src/hydrahive/tools/_html_text.py`, nur Standardbibliothek (`html.parser`)
- `extract(html: str) -> dict` mit `text`, `title`, `published`
- `default_headers(given: dict) -> dict`: UA, Accept und Accept-Language nur setzen, wenn noch nicht vorhanden. Groß-/Kleinschreibung der Header-Namen egal.

Tests `core/tests/test_html_text.py` (neu):
- Fixture im Stil von Borncity: Überschrift und Absätze bleiben, `<script>`, `<style>`, Navigation, Footer und Formular sind weg.
  Text < 10 % des HTML, `title` aus `og:title`, `published` aus `article:published_time`.
- `<article>` hat Vorrang vor `<main>` und `<body>`, Entities aufgelöst, Leerraum zusammengefasst.
- Kaputtes HTML ohne `body` stürzt nicht ab.
- Header: Vom Aufrufer gesetzter `user-agent` (klein geschrieben) wird nicht überschrieben.

Tests `core/tests/test_fetch_url_format.py` (neu, gefälschter Client):
- Standard-Header kommen an, der vom Aufrufer gesetzte Header gewinnt.
- `format` fehlt → Body roh wie heute, Grenze bei 200 KB.
- `format="text"` + HTML → `body` ist Text, `title` und `published` sind gesetzt, `format_applied: "text"`.
- `format="text"` + JSON → roh, `format_applied: "raw"`.
- Unter 200 Zeichen Text → `hint` mit Verweis auf web_browser.
- Text länger als 50.000 Zeichen → gekürzt, `truncated: true`.
- Ungültiges `format` → `fail`.

Code: `fetch_url.py` hat 193 Zeilen. Dazu kommen nur der Header-Aufruf, die Prüfung von `format` und die Weiche,
die Auswertung selbst steckt in `_html_text.py`. Kommt die Datei über ~200 Zeilen, wandert der Ergebnisbau in einen Helfer.

## Abschluss

- `ruff`, die volle Kern-Suite (`/opt/hydrahive2/.venv`), `PYTHONDONTWRITEBYTECODE=1`.
- Mutanten:
  - Fallback-Bedingung (and/or)
  - Zählergrenze (950 → 1000, `>=` → `>`)
  - Reservierung erst nach dem Aufruf
  - Header-Vorrang
  - Script-Entfernung
  - `format`-Standard
  - Tavily ohne Schlüssel
  - Schlüssel im Fehlertext
- PR mit Befund, danach Live-Abnahme laut Spec §10.
