#!/bin/bash
# Liest das Admin-Erstpasswort für den Abschluss-Kasten von install-mac.sh.
#
# Das Backend legt beim ersten Start den Benutzer „admin“ an und schreibt das
# Passwort nach $HH_CONFIG_DIR/.admin_initial_password (0600, gehört dem
# Dienstnutzer = dem Nutzer, der den Installer startet). Früher suchte der
# Mac-Installer im System-Log (`log show`), dort landet die Meldung aber nicht:
# launchd leitet stderr nach /usr/local/var/log/hydrahive2-error.log um.
# Wie unter Linux (install.sh): Datei lesen, danach löschen.
#
# Gibt das Passwort aus oder nichts (admin gab es schon). Exit immer 0.
# Env: HH_CONFIG_DIR (Pflicht), HH_PW_TRIES (Versuche à 2 s, Default 30).
set -uo pipefail

PW_FILE="${HH_CONFIG_DIR:?HH_CONFIG_DIR fehlt}/.admin_initial_password"
TRIES="${HH_PW_TRIES:-30}"

for ((i = 0; i < TRIES; i++)); do
  if [ -s "$PW_FILE" ]; then
    tr -d '\r\n' < "$PW_FILE"
    rm -f "$PW_FILE"
    exit 0
  fi
  sleep 2
done
exit 0
