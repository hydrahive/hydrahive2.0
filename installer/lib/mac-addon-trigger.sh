#!/bin/bash
# macOS: LaunchDaemon io.hydrahive.addon – startet installer/lib/mac-addon-ctl.sh (root), sobald die API
# $HH_DATA_DIR/.addon_request schreibt (Einstellungen → Zusatz-Module). Gegenstück zu hydrahive2-addon.timer (Linux).
# Läuft aus install-mac.sh und update-mac.sh (richtet nach). Idempotent.
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
HH_USER="${HH_USER:?HH_USER fehlt}"
HH_LOG_DIR="${HH_LOG_DIR:-/usr/local/var/log}"
PLIST="${HH_ADDON_PLIST:-/Library/LaunchDaemons/io.hydrahive.addon.plist}"

priv() { if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi; }

log "Schreibe $PLIST"
priv tee "$PLIST" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.hydrahive.addon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${HH_REPO_DIR}/installer/lib/mac-addon-ctl.sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HH_REPO_DIR</key>
        <string>${HH_REPO_DIR}</string>
        <key>HH_DATA_DIR</key>
        <string>${HH_DATA_DIR}</string>
        <key>HH_CONFIG_DIR</key>
        <string>${HH_CONFIG_DIR}</string>
        <key>HH_USER</key>
        <string>${HH_USER}</string>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>WatchPaths</key>
    <array>
        <string>${HH_DATA_DIR}/.addon_request</string>
    </array>
    <key>StandardOutPath</key>
    <string>${HH_LOG_DIR}/hydrahive2-addon.log</string>
    <key>StandardErrorPath</key>
    <string>${HH_LOG_DIR}/hydrahive2-addon.log</string>
</dict>
</plist>
EOF
priv touch "$HH_LOG_DIR/hydrahive2-addon.log"
priv chmod 644 "$HH_LOG_DIR/hydrahive2-addon.log" "$PLIST"
priv launchctl unload "$PLIST" >/dev/null 2>&1 || true
priv launchctl load "$PLIST"
log "Zusatz-Module-Auslöser aktiv (io.hydrahive.addon)"
