# macOS: Update-Verlauf, Python-Pakete, Frontend – Spec

Status: **FREIGEGEBEN** durch Till (20.10.2026: „ok baue sie“). Anlass: Mac-Nutzer sieht im Update-Fenster keinen
Verlauf; zuvor scheiterte jeder Modellaufruf an gemischten LiteLLM-Dateien.

## 1. Befunde (Code, 20.10.2026)

1. **Verlauf leer:** Das Backend liest den Verlauf aus `settings.update_log` = `$HH_LOG_DIR/hydrahive2-update.log`,
   Standard `/var/log`. Die Mac-plist (`modules-mac/50-launchd.sh`) setzt `HH_LOG_DIR` nicht, `update-mac.sh` und der
   Update-LaunchDaemon schreiben aber nach `/usr/local/var/log/hydrahive2-update.log`. → Das Fenster liest eine Datei,
   die es nicht gibt (`exists: false`).
2. **Pakete:** `update-mac.sh` ruft `pip install --quiet -e core`. Das prüft nur die Grenzen aus `pyproject.toml`;
   ein beschädigtes oder halb aktualisiertes Paket (Beispiel LiteLLM, neue `main.py` + alte Handler-Datei) bleibt liegen.
3. **Frontend:** `git diff --name-only HEAD@{1} HEAD` läuft als **root** (ohne `sudo -u`) im Repo des Dienstnutzers.
   Neuere git-Versionen lehnen das als „dubious ownership“ ab; der Fehler ist mit `2>/dev/null` stummgeschaltet →
   `grep` findet nichts → das Frontend wird **nie** neu gebaut. Außerdem: ohne Frontend-Änderung wird auch dann nicht
   gebaut, wenn `frontend/dist` fehlt, und `--silent`/`--quiet` lassen den Verlauf leer.

## 2. Lösung

1. `50-launchd.sh`: plist bekommt `HH_LOG_DIR=/usr/local/var/log` (dort liegen alle Mac-Logs, `20-paths.sh` legt den
   Ordner an). `update-mac.sh` erkennt eine plist **ohne** `HH_LOG_DIR` und schreibt sie neu (wie bei den anderen
   Merkmalen) – danach zeigt das Fenster den Verlauf.
2. Pakete: nach `pip install -e core` ein **`pip check`**. Meldet er Fehler, wird jedes betroffene Paket mit
   `--force-reinstall --no-deps` neu installiert (nur diese, nicht alles). Zusätzlich gilt das immer für `litellm`,
   wenn `import litellm` scheitert (beschädigte Dateien merkt `pip check` nicht). Alles ins Update-Log.
3. Frontend: Stand vor dem Pull merken (`git rev-parse HEAD` als Dienstnutzer), danach
   `git diff --name-only <alt> HEAD -- frontend/` als Dienstnutzer. Gebaut wird bei Änderungen **oder** wenn
   `frontend/dist/index.html` fehlt. Ausgaben von npm ins Update-Log.
4. Jede Zeile des Skripts landet im Update-Log (bisher nur `log()`-Zeilen und git).

Gilt nur für macOS. Linux (`update.sh`) bleibt unverändert.

## 3. Tests
- plist enthält `HH_LOG_DIR` mit `/usr/local/var/log`; `settings.update_log` daraus zeigt auf die Datei, in die
  `update-mac.sh` schreibt.
- `update-mac.sh` schreibt eine plist ohne `HH_LOG_DIR` neu; eine aktuelle bleibt.
- `pip check` mit Fehler → `--force-reinstall --no-deps` genau für das gemeldete Paket; ohne Fehler kein Neuinstall.
- Kaputtes `import litellm` → LiteLLM wird neu installiert.
- Frontend: Änderung unter `frontend/` → Build; keine Änderung, aber `dist` fehlt → Build; sonst kein Build.
- Ausgaben von pip und npm stehen im Update-Log.


## 4. Nachtrag 20.10.2026 (echter Test auf dem Test-Mac .186)

1. **Bash 3.2:** macOS hat `/bin/bash` 3.2. Mit `set -u` bricht dort ein leeres Array als `"${a[@]}"` /
   `${a[*]}` ab („unbound variable“) – `mac-python-heal.sh` scheiterte beim ersten echten Lauf genau so. Abhilfe:
   `${a[@]+"${a[@]}"}` und `${a[*]-}`; ein Test sucht diese Falle in allen Mac-Skripten.
2. **Frontend blieb alt:** Der erste Lauf nach dem Merge lief noch mit dem alten `update-mac.sh`, holte alles und
   baute nicht. Der zweite Lauf sah keinen Unterschied mehr (alt = neu) → kein Build, obwohl 65 Frontend-Änderungen
   seit dem letzten Build fehlten. Darum statt „Vergleich vor/nach dem Pull“ ein **Vermerk im Build**:
   - nach jedem erfolgreichen Build `frontend/dist/.hh-frontend-rev` = letzter Commit unter `frontend/`
     (`git log -1 --format=%H -- frontend/`, als Dienstnutzer);
   - gebaut wird, wenn `dist/index.html` fehlt oder der Vermerk fehlt oder nicht zum aktuellen Stand passt;
   - lässt sich der Stand nicht bestimmen (git-Fehler), wird nur bei fehlendem `dist` gebaut und das im Log vermerkt.
3. **`npm install` verändert `package-lock.json`** (auf dem Test-Mac: 4 Zeilen `"peer": true` weg, andere npm-Version
   als beim Erzeugen). Beim nächsten Update scheitert dann `git pull --ff-only` an der lokalen Änderung – anders als
   Linux setzt der Mac danach nicht auf `origin/main` zurück. Abhilfe: **`npm ci`** (wie die CI) – installiert genau
   nach der Lock-Datei und ändert sie nie.
4. **Jede Zeile doppelt im Verlauf** (Test über den Knopf, 21.10.): Der Update-LaunchDaemon leitet stdout/stderr
   schon nach `hydrahive2-update.log` (`55-launchd-triggers.sh`), `update-mac.sh` schreibt zusätzlich per `tee -a`
   dorthin. Abhilfe: Der Update-LaunchDaemon setzt `HH_UPDATE_VIA_LAUNCHD=1`; dann schreibt `update-mac.sh` nur auf die
   Standardausgabe (die launchd schon in die Datei leitet). Ohne die Kennung (Aufruf im Terminal) wie bisher Datei +
   Bildschirm. Der Vergleich `[ /dev/stdout -ef "$LOG" ]` taugt nicht: auf macOS (Bash 3.2) meldet er „verschieden“,
   obwohl es dieselbe Datei ist (geprüft auf .186).
   `update-mac.sh` schreibt die Update-plist neu, wenn die Kennung fehlt (über `55-launchd-triggers.sh`). Die neue plist
   gilt erst beim **nächsten** Update – das laufende Update selbst schreibt in diesem einen Fall noch doppelt.
