# Websuche: gesperrte Suchanbieter erkennen, Installer-Pfad korrigieren

Stand: 02.10.2026 · Task c1d6bf33 · Memory `infra.searxng-engines-blocked`

## 1. Was passiert ist

Am 02.10.2026 lieferte die Websuche bei jeder Anfrage **0 Treffer**, obwohl SearXNG lief
(0 Neustarts, Port 8888 offen). Ursache: Die aktiven Standard-Suchanbieter sperren uns.

| Anbieter   | Antwort                          |
|------------|----------------------------------|
| DuckDuckGo | CAPTCHA                          |
| Startpage  | CAPTCHA, ausgesetzt              |
| Brave      | zu viele Anfragen                |
| Google     | leer, ohne Fehlermeldung         |
| Bing       | 10 Treffer — war aber **aus**    |
| Yandex     | 10–15 Treffer — war aber **aus** |

Live behoben (mit Tills OK): Bing und Yandex in `/opt/searxng/searxng/settings.yml`
eingeschaltet, Sicherung `/var/backups/searxng-settings-20261002-223643.yml`. Danach 20–25
Treffer je Anfrage.

**Warum es niemand gemerkt hat:** `web_search` gab „ok, count 0“ zurück. SearXNG meldet die
gesperrten Anbieter in `unresponsive_engines`, das Werkzeug hat das Feld verworfen. Für den
Agenten sah „alle Anbieter gesperrt“ genauso aus wie „zu dieser Frage gibt es nichts“.

## 2. Zweiter Fund: Installer schreibt in die Standarddatei von SearXNG

`installer/modules/76-searxng.sh` setzt

```
SEARXNG_SETTINGS="$SEARXNG_DIR/searx/settings.yml"     # = /opt/searxng/searx/settings.yml
```

Das ist **nicht** eine eigene Einstellungsdatei, sondern die mitgelieferte
Standarddatei von SearXNG (`searx/settings.yml`, 2.766 Zeilen, unter Versionskontrolle).
SearXNG lädt sie als `DEFAULT_SETTINGS_FILE` und legt die Nutzer-Einstellungen darüber.

Folgen bei einer Neuinstallation:
- Der Installer überschreibt die Standarddatei mit seinen ~40 Zeilen und `use_default_settings: true`.
- SearXNG lädt diese Datei als Standard **und** (über `SEARXNG_SETTINGS_PATH`) als
  Nutzer-Datei — die vollständigen Standardwerte (alle Anbieter-Definitionen, Kategorien …)
  fehlen. Die Engines `google`, `bing`, `duckduckgo`, `wikipedia` hängen dann ohne ihre
  Standardfelder (`shortcut`, `categories` …) in der Liste.
- Ein späteres `git pull` in `/opt/searxng` kollidiert mit der lokal veränderten Datei.

Auf Prod tritt das nicht auf, weil SearXNG dort von Hand eingerichtet wurde
(`/opt/searxng/searxng/settings.yml`, Dienstbeschreibung „Metasuchmaschine“ statt „Metasearch
Engine“, Standarddatei unverändert). Neuinstallationen bei Kunden sind betroffen.

## 3. Ziel

1. Gesperrte Anbieter werden **sichtbar**, für Agenten und auf dem Dashboard.
2. Neuinstallationen bekommen eine eigene, korrekte Einstellungsdatei mit Anbietern, die
   heute funktionieren.
3. Bestehende Installationen werden beim Update angeglichen, ohne Eigenes zu zerstören.

## 4. `web_search` (core/src/hydrahive/tools/web_search.py)

- Liest `unresponsive_engines` (Liste von `[name, grund]`).
- **0 Treffer und mindestens ein Anbieter ausgefallen → Fehler**:
  `Websuche liefert keine Treffer — Suchanbieter gesperrt: duckduckgo (CAPTCHA), brave (zu viele Anfragen). Dienst prüfen (SearXNG).`
  So kann der Agent nicht stillschweigend ohne Suche weiterarbeiten.
- **Treffer vorhanden, aber Anbieter ausgefallen → ok**, zusätzlich Feld
  `unavailable: [{engine, reason}]` (Teilausfall ist Information, kein Fehler).
- **0 Treffer ohne Ausfälle → ok, count 0** wie bisher (es gibt wirklich nichts).
- Ungültige Einträge in `unresponsive_engines` (kein Paar, kein Text) werden übersprungen,
  nie Absturz. Grund wird auf 80 Zeichen gekürzt.

## 5. Dashboard-Prüfung (core/src/hydrahive/api/routes/_websearch_health.py)

- `detail` nennt ausgefallene Anbieter auch bei Erfolg:
  `20 Ergebnisse · ausgefallen: duckduckgo, brave, startpage` (Hinweis im Tooltip, Status bleibt ok).
- Bei 0 Treffern und Ausfällen: `keine Ergebnisse — gesperrt: duckduckgo (CAPTCHA), …`, Status warn.
- Feld `unavailable` zusätzlich im Ergebnis (für spätere Anzeige).
- Frontend unverändert (zeigt `detail` schon im Tooltip).

## 6. Installer (installer/modules/76-searxng.sh)

- Eigene Datei: `SEARXNG_SETTINGS="$SEARXNG_DIR/searxng/settings.yml"` (wie Prod), Ordner
  anlegen. **Nie** mehr `searx/settings.yml` schreiben.
- Die Datei wird nur **neu geschrieben, wenn sie fehlt oder vom Installer stammt**
  (Kopfzeile `# HydraHive SearXNG — automatisch generiert`). Von Hand angepasste Dateien
  (wie Prod) bleiben unangetastet — dort sorgt die Migration (Abschnitt 7) nur für die
  Anbieter.
- Anbieter in der generierten Datei: `bing`, `yandex` an (mit Kommentar warum), `wikipedia`
  bleibt Standard. Keine Felder außer `name` und `disabled`, damit die Standardwerte von
  SearXNG erhalten bleiben.
- Bestehender `secret_key` wird aus der eigenen Datei übernommen; zusätzlich (einmalig) aus
  der alten falschen Stelle, damit Sitzungen nicht wechseln.
- Hat ein früherer Lauf `searx/settings.yml` verändert: per `git checkout -- searx/settings.yml`
  wiederherstellen (nur wenn das Repo vorhanden ist, Sicherung vorher nach
  `/var/backups/searxng-default-settings-<zeit>.yml`).
- Dienst-Unit zeigt auf die neue Datei.

## 7. Migration für Bestand (installer/migrations/searxng-engines.sh, aus update.sh)

Idempotent, läuft nur, wenn SearXNG installiert ist (Unit vorhanden).

1. Pfad der aktiven Datei aus der Unit lesen (`SEARXNG_SETTINGS_PATH`).
2. Zeigt sie auf `searx/settings.yml` (falscher Pfad): Abschnitt-6-Reparatur
   (Standarddatei wiederherstellen, eigene Datei unter `searxng/settings.yml` anlegen,
   Unit umstellen).
3. Fehlen in der aktiven Datei Einträge für `bing`/`yandex`: Sicherung anlegen, dann
   mit dem Python des SearXNG-venv die YAML-Datei laden, Einträge
   `{name, disabled: false}` ergänzen (vorhandene Einträge anderer Anbieter und alle anderen
   Abschnitte bleiben), zurückschreiben. Hat der Nutzer `bing` oder `yandex` **selbst**
   eingetragen (z. B. `disabled: true`), wird nichts geändert.
4. Nur wenn etwas geändert wurde: Dienst neu starten und mit einer echten JSON-Suche prüfen;
   bei 0 Treffern Sicherung zurückspielen und Warnung ausgeben (Update bricht nicht ab).

## 8. Bewusst nicht Teil

- Kein automatisches Umschalten zwischen Anbietern zur Laufzeit.
- Keine Proxies, keine bezahlten Such-APIs.
- Keine Benachrichtigung bei Ausfall (Dashboard-Status reicht; Benachrichtigung gehört zur
  zentralen Konfiguration, Task 89027e84).

## 9. Tests (TDD)

`core/tests/test_web_search_tool.py` (neu):
- alle gesperrt, 0 Treffer → `ok False`, Meldung nennt Anbieter + Grund
- Treffer + Teilausfall → `ok True`, `unavailable` gefüllt
- 0 Treffer ohne Ausfälle → `ok True`, `count 0`
- kaputte `unresponsive_engines` (None, String, falsche Länge) → kein Absturz
- langer Grund wird gekürzt

`core/tests/test_websearch_health.py` (erweitert):
- Treffer + Ausfälle → ok, detail nennt Ausfälle
- 0 Treffer + Ausfälle → warn, detail nennt Grund

`core/tests/test_searxng_installer.py` (neu, Shell in temporärem Ordner, ohne root):
- Installer-Text: kein `searx/settings.yml` als Ziel, Unit-Pfad = eigene Datei
- Migration: fügt bing/yandex hinzu; erhält fremde Einträge, Kommentare-freie Abschnitte
  und `secret_key`; lässt vom Nutzer gesetztes `bing: disabled: true` stehen; zweiter Lauf
  ändert nichts (idempotent); legt Sicherung an.

Jede Schutzregel wird per Gegenprobe rot gemacht.

## 10. Prüfung

- volle Suite, ruff
- hydratest: SearXNG dort nicht installiert → Installer-Modul einmal frisch ausführen
  (echter Neuinstallationsfall), danach `web_search` per Agent/API mit Treffern;
  Migration auf hydratest zweimal laufen lassen (idempotent); simulierte Sperre
  (alle Anbieter außer einem nicht erreichbaren aus) → Werkzeug meldet Fehler.
- Prod nach Update (Till): Migration erkennt Prod als bereits korrekt (bing/yandex
  vorhanden) und ändert nichts.
