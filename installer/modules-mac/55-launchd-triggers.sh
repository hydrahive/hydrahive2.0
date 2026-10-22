#!/usr/bin/env bash
# Installiert launchd-Trigger für Self-Update und Restart.
# Nutzt WatchPaths — launchd feuert sobald die Datei erscheint.
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

UPDATE_PLIST="/Library/LaunchDaemons/io.hydrahive.update.plist"
RESTART_PLIST="/Library/LaunchDaemons/io.hydrahive.restart.plist"

touch /usr/local/var/log/hydrahive2-update.log
chmod 644 /usr/local/var/log/hydrahive2-update.log

log "Schreibe $UPDATE_PLIST"
sudo tee "$UPDATE_PLIST" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.hydrahive.update</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${HH_REPO_DIR}/installer/update-mac.sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HH_REPO_DIR</key>
        <string>${HH_REPO_DIR}</string>
        <key>HH_DATA_DIR</key>
        <string>${HH_DATA_DIR}</string>
        <key>HH_USER</key>
        <string>${HH_USER}</string>
        <!-- launchd leitet stdout/stderr schon in die Log-Datei → update-mac.sh schreibt nicht zusätzlich hinein -->
        <key>HH_UPDATE_VIA_LAUNCHD</key>
        <string>1</string>
    </dict>
    <key>WatchPaths</key>
    <array>
        <string>${HH_DATA_DIR}/.update_request</string>
    </array>
    <key>StandardOutPath</key>
    <string>/usr/local/var/log/hydrahive2-update.log</string>
    <key>StandardErrorPath</key>
    <string>/usr/local/var/log/hydrahive2-update.log</string>
</dict>
</plist>
EOF

log "Schreibe $RESTART_PLIST"
sudo tee "$RESTART_PLIST" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.hydrahive.restart</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>rm -f ${HH_DATA_DIR}/.restart_request; launchctl unload /Library/LaunchDaemons/io.hydrahive.backend.plist 2>/dev/null; sleep 1; launchctl load /Library/LaunchDaemons/io.hydrahive.backend.plist</string>
    </array>
    <key>WatchPaths</key>
    <array>
        <string>${HH_DATA_DIR}/.restart_request</string>
    </array>
    <key>StandardOutPath</key>
    <string>/usr/local/var/log/hydrahive2-update.log</string>
    <key>StandardErrorPath</key>
    <string>/usr/local/var/log/hydrahive2-update.log</string>
</dict>
</plist>
EOF

sudo chmod 644 "$UPDATE_PLIST" "$RESTART_PLIST"
# Läuft dieses Skript INNERHALB des Update-Dienstes (Knopf im Cockpit → update-mac.sh → hier), darf es
# io.hydrahive.update nicht entladen: launchd beendet damit das laufende Update samt diesem Skript, das `load`
# danach kommt nie – der Dienst ist weg, jeder weitere Knopfdruck landet ins Leere (Befund Mac-Tester 22.10.2026).
# Die neue plist gilt dann ab dem nächsten Laden (Neustart oder Update aus dem Terminal).
if [ "${HH_UPDATE_VIA_LAUNCHD:-}" = "1" ]; then
  log "Update-Auslöser: neue Datei geschrieben, gilt ab dem nächsten Neustart (läuft gerade selbst)"
else
  sudo launchctl unload "$UPDATE_PLIST" 2>/dev/null || true
  sudo launchctl load "$UPDATE_PLIST"
fi
sudo launchctl unload "$RESTART_PLIST" 2>/dev/null || true
sudo launchctl load "$RESTART_PLIST"

log "Update- und Restart-Trigger aktiv (WatchPaths)"
