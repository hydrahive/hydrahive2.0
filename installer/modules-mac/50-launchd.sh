#!/usr/bin/env bash
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

PLIST_LABEL="io.hydrahive.backend"
PLIST_FILE="/Library/LaunchDaemons/${PLIST_LABEL}.plist"
BREW_PREFIX="$(brew --prefix 2>/dev/null || echo /usr/local)"

# JWT-Secret
SECRET_FILE="$HH_CONFIG_DIR/secret_key"
if [ ! -f "$SECRET_FILE" ]; then
  log "Generiere JWT-Secret"
  python3 -c "import secrets; print(secrets.token_urlsafe(48))" > "$SECRET_FILE"
  chmod 600 "$SECRET_FILE"
fi
SECRET_KEY="$(cat "$SECRET_FILE")"

# PG-DSN falls vorhanden
PG_DSN=""
if [ -f "$HH_CONFIG_DIR/.pg_dsn_tmp" ]; then
  PG_DSN=$(cat "$HH_CONFIG_DIR/.pg_dsn_tmp")
  rm -f "$HH_CONFIG_DIR/.pg_dsn_tmp"
fi

log "Schreibe $PLIST_FILE"
sudo tee "$PLIST_FILE" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${HH_REPO_DIR}/.venv/bin/uvicorn</string>
        <string>hydrahive.api.main:app</string>
        <string>--host</string>
        <string>${HH_HOST}</string>
        <string>--port</string>
        <string>${HH_PORT}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${HH_REPO_DIR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HH_DATA_DIR</key>
        <string>${HH_DATA_DIR}</string>
        <key>HH_CONFIG_DIR</key>
        <string>${HH_CONFIG_DIR}</string>
        <key>HH_HOST</key>
        <string>${HH_HOST}</string>
        <key>HH_PORT</key>
        <string>${HH_PORT}</string>
        <key>HH_SECRET_KEY</key>
        <string>${SECRET_KEY}</string>
        <key>HH_PG_MIRROR_DSN</key>
        <string>${PG_DSN}</string>
        <key>HOME</key>
        <string>/Users/${HH_USER}</string>
        <key>PATH</key>
        <string>${HH_REPO_DIR}/.venv/bin:${BREW_PREFIX}/opt/python@3.12/bin:${BREW_PREFIX}/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>UserName</key>
    <string>${HH_USER}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/usr/local/var/log/hydrahive2.log</string>
    <key>StandardErrorPath</key>
    <string>/usr/local/var/log/hydrahive2-error.log</string>
</dict>
</plist>
EOF

sudo chmod 644 "$PLIST_FILE"

# Bereits geladen? Dann neu laden.
if sudo launchctl list | grep -q "$PLIST_LABEL"; then
  log "Service neu laden"
  sudo launchctl unload "$PLIST_FILE" 2>/dev/null || true
fi

log "Lade Service"
sudo launchctl load "$PLIST_FILE"
sleep 2

if sudo launchctl list | grep -q "$PLIST_LABEL"; then
  log "Service läuft."
else
  log "Service-Start fehlgeschlagen — siehe: tail -50 /usr/local/var/log/hydrahive2-error.log"
  exit 1
fi
