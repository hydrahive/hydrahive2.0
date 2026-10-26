# Update: nichts mehr still verwerfen, nie auf einen fremden Branch springen

Task cabd0df1. `installer/update.sh` läuft auf **allen** Installationen. Jede Änderung braucht Tills OK,
er hat sie am 25.10.2026 gegeben.

## Befund

- Seit 880b7c83 (28.05.) gilt: Scheitert `git pull --ff-only`, holt update.sh den Stand und setzt hart
  auf **`origin/main`** zurück (`reset --hard`). Die Variable `DIVERGED` wird berechnet und nie benutzt. Gedacht war
  das für einen History-Rewrite auf GitHub (Force-Push nach Bereinigung sensibler Daten).
- `pull --ff-only` scheitert aber auch bei bloß **geänderten Dateien**. update.sh erzeugt eine solche Änderung selbst:
  Z. 231 `npm install` schreibt `frontend/package-lock.json` um (gemessen: 4× `"peer": true` weniger, auf hydratest
  und auf dem Hauptserver). Beim nächsten Update mit neuem Stand läuft deshalb `reset --hard origin/main`.
- Folgen:
  1. Jede lokale Änderung in getrackten Dateien geht **ohne Meldung** verloren.
  2. Ein Server auf einem anderen Branch (Testserver, Vorschau) springt auf main (Befund 24.10. auf hydratest).
- Gemessen am 25.10. mit npm 10.8.2: `npm ci` lässt `package-lock.json` unverändert, `npm install` ändert sie.

## Änderung

1. **Frontend: `npm ci`** statt `npm install` in update.sh, wie in update-mac.sh seit #593.
   - Vorher wird eine umgeschriebene `package-lock.json` auf den Stand im Repo zurückgesetzt. Das ist die einzige
     Datei, die update.sh selbst verändert. Andere Dateien bleiben unberührt.
   - Kein Netz-/Registry-Fehler darf still durchrutschen: `npm ci` scheitert sonst laut, wie bisher bei `set -e`.
   - Erst-Installation (`40-frontend.sh`) ebenfalls `npm ci`. Die WhatsApp-Bridge hat eine eigene Lock-Datei,
     dort auch `npm ci`.
2. **Git-Schritt als eigene, testbare Funktion** `hh_git_update` (`installer/lib/git-update.sh`):
   - Er bestimmt den Branch, der ausgecheckt ist, und dessen Gegenstück auf origin (`origin/<branch>`). Kein fester
     Bezug mehr auf main. Ohne Branch (detached HEAD) bricht er mit Meldung ab.
   - **Lokal geänderte Dateien** (nach dem Lock-Zurücksetzen): Abbruch mit einer Meldung, die die Dateien nennt
     („Lokale Änderungen in: … – Update angehalten, nichts verworfen“). Es gibt kein `reset`.
   - Dann `fetch`. Scheitert er, erfolgt der Abbruch wie bisher („Netzwerk oder Zugang prüfen“).
   - **Vorspulen möglich** (`HEAD` ist Vorfahr von `origin/<branch>`): `merge --ff-only`.
   - **Schon aktuell oder lokal voraus** (lokale Commits, die origin nicht hat): Abbruch mit Meldung, kein Reset.
     Lokale Commits sind Arbeit, die verloren ginge.
   - **Echter History-Rewrite** (origin wurde umgeschrieben, lokal hat keine eigenen Commits, die nicht schon in der
     alten origin-Geschichte lagen): Erkennbar daran, dass alle lokalen Commits in `ORIG_REMOTE` (Stand von
     `origin/<branch>` vor dem fetch) enthalten waren. Nur dann `reset --hard origin/<branch>`, mit
     Sicherungs-Tag `hh-update-vorher-<datum>` auf dem alten Stand. So bleibt der Fall aus 880b7c83 abgedeckt, ohne
     fremde Arbeit zu verwerfen.
3. Alle Abbrüche gehen über `err`, das Update-Fenster zeigt den Grund (`HH-UPDATE-ENDE: fehler …`).

## Prüfung

- Rote Tests vorher, mit echten Git-Repos im tmp-Ordner (Bare-Repo als origin, Klon als Server):
  - Vorspulen ok.
  - Bereits aktuell.
  - Umgeschriebene Lock → zurückgesetzt, Vorspulen ok.
  - Andere geänderte Datei → Abbruch, Datei unverändert.
  - Lokaler Commit → Abbruch, Commit bleibt.
  - Branch ≠ main → zieht `origin/<branch>`, nie main.
  - History-Rewrite ohne eigene Commits → Reset mit Sicherungs-Tag.
  - Rewrite mit eigenem Commit → Abbruch.
  - Detached HEAD → Abbruch.
  - Fetch-Fehler → Abbruch.
- Ein Test prüft, dass update.sh `hh_git_update` nutzt, `npm ci` statt `npm install` im Frontend, und kein
  `reset --hard origin/main` mehr.
- Mutanten.
- hydratest:
  - echtes Update von main auf einen neueren Stand mit vorher umgeschriebener Lock-Datei → ok, Lock unverändert
  - Feature-Branch per deploy-test.sh → bleibt auf dem Branch
  - eine absichtlich geänderte Datei → Abbruch mit Meldung, danach zurück
- Frische Kopie: Erst-Installation baut das Frontend mit `npm ci`.

## Nachtrag 26.10.2026: alle Lock-Dateien, die das Update anfasst (Task 928f868e)

Auf der .4 brach das erste Update mit dem neuen Skript ab: „Lokale Änderungen in:
`core/src/hydrahive/communication/whatsapp/bridge/package-lock.json`“.
- Ursache: Auch die WhatsApp-Bridge lief bis #625 mit `npm install`, das ihre Lock-Datei umschreibt. Zurückgesetzt
  wurde aber nur die Frontend-Lock.
- Ab jetzt ist `HH_GIT_SELF_OWNED` eine **Liste** aller getrackten `package-lock.json`, die das Update selbst per npm
  anfasst: Frontend und WhatsApp-Bridge.
- Ein Wächter-Test prüft: Jede getrackte `package-lock.json` im Repo steht in der Liste. Eine neue Lock-Datei fällt
  dann sofort auf.
