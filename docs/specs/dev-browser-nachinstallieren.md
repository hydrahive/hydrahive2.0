# Browser-Werkzeug: dev-browser bei Installation und Update sicherstellen

Task 3d517e82. Till am 25.10.2026: „Baue es in den Installer und das Update ein, dass es nachinstalliert wird, wenn
es fehlt, damit es draußen bei den Usern auch gefixt wird.“

## Befund (Hauptserver, nur gelesen)

- Das Werkzeug `web_browser` meldet „dev-browser nicht installiert“. Auf dem Hauptserver fehlt das Programm seit dem
  Umzug .2 → .226 (18.10.). Reste liegen noch unter `~hydrahive/.config/hh-dev-browser-home/.dev-browser`.
- `installer/modules/87-mcp-servers.sh` richtet dev-browser ein, wird aber **seit seiner Entstehung (fa42c0c9, 21.05.)
  weder von `install.sh` noch von `update.sh` aufgerufen**.
  - Neue Installationen bekommen dev-browser also gar nicht.
  - Bestehende bekommen es nur, wenn jemand das Modul von Hand startet.
- Das npm-Paket `dev-browser` ist MIT-lizenziert. `latest` = 0.2.9, daneben `next` = 1.0.0-rc.
- Eine Laufzeit-Prüfung im Systemstatus gibt es nicht. Der Agent sieht als Fehler einen npm-Befehl, die
  Nutzerin sieht nichts.

## Änderung

1. **Gemeinsame Funktion** `ensure_dev_browser` in `installer/lib/dev-browser.sh`, wie `lib/graphify.sh`.
   Wird gesourct, ist idempotent, ein Fehler bricht die Installation nicht ab.
   - Ist das Programm nicht im PATH → `npm install -g dev-browser@0.2.9`. Die Version ist fest, damit keine
     ungeprüfte 1.0-RC kommt. Ein Wechsel erfolgt bewusst über diese Datei.
   - Laufzeit (`.dev-browser/node_modules`) oder Chromium (`.cache/ms-playwright`) fehlen →
     `dev-browser install` als `$HH_USER` mit `HOME=$DEV_BROWSER_HOME`. Danach wird geprüft, ob beides da ist.
   - Fehler werden als `WARNUNG` geloggt, mit den letzten Zeilen des Protokolls. Sie werden nie verschluckt.
   - Nach Erfolg eine Abschlussmeldung mit der Version.
2. **Aufrufe:**
   - `install.sh`: eigene Phase nach dem Frontend.
   - `update.sh`: nach der Playwright-Synchronisierung. Läuft bei jedem Update, holt Fehlendes nach und lässt
     Vorhandenes unberührt.
   - `87-mcp-servers.sh`: dev-browser-Teil ersetzt durch `source lib/dev-browser.sh` + `ensure_dev_browser`.
     Das Modul selbst (MCP-Pakete, Config) bleibt, wie es ist, und wird hier nicht eingehängt.
3. **Verständlicher Fehler im Werkzeug:** Statt des npm-Befehls steht dort „Das Browser-Werkzeug ist auf diesem
   Server noch nicht eingerichtet. Ein Admin kann es mit „System aktualisieren“ in der Admin-Konsole nachholen.“

Nicht enthalten:
- **Mac:** `install-mac.sh`/`update-mac.sh` haben keinen dev-browser-Teil. Dort fehlt das Werkzeug weiterhin. Das ist
  ein eigener Schritt, weil Homebrew-npm andere Pfade und Rechte hat.
- Der Systemstatus-Eintrag im Admin-Cockpit kommt als eigener Schritt, wenn gewünscht.

## Prüfung

- Rote Tests vorher, gegen die Funktion mit PATH-Attrappen für `npm`, `dev-browser`, `sudo`:
  - fehlt komplett → npm + install laufen, Erfolg gemeldet
  - schon da → nichts läuft
  - nur Chromium fehlt → nur install
  - npm scheitert → WARNUNG, Rückgabe 0
  - install scheitert oder legt nichts an → WARNUNG mit Logzeilen
  - feste Version
  - Wächter: `install.sh`, `update.sh` und `87-mcp-servers.sh` nutzen `ensure_dev_browser`; kein `|| true` ohne Meldung
- Mutanten, volle Testreihe.
- hydratest:
  - echtes `update.sh` → dev-browser da, Werkzeug macht einen echten Seitenabruf
  - zweites Update → „vorhanden“, nichts neu installiert
- Hauptserver: nach Merge und Tills Kern-Update dasselbe prüfen (nur lesen).
