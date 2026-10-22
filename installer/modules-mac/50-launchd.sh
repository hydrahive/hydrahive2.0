#!/usr/bin/env bash
set -euo pipefail
log() { printf "  · %s\n" "$*"; }
# shellcheck source=../lib/mac-roles.sh
source "$(dirname "$0")/../lib/mac-roles.sh"

PLIST_LABEL="io.hydrahive.backend"
PLIST_FILE="${HH_BACKEND_PLIST:-/Library/LaunchDaemons/${PLIST_LABEL}.plist}"
START_WRAPPER="${HH_REPO_DIR}/installer/lib/mac-backend-start.sh"
# Homebrew über den vollen Pfad: aus dem Cockpit-Runner und update-mac.sh läuft dieses Skript als root ohne brew im
# PATH. Früher fiel BREW_PREFIX dann auf /usr/local zurück – auf Apple-Macs liegt Homebrew aber unter /opt/homebrew,
# ffmpeg & Co. fehlten im Backend-PATH (Befund MacBook Air M2, 22.10.2026: Spracheingabe „STT nicht erreichbar“).
BREW_PREFIX=""
for candidate in ${HH_BREW_CANDIDATES:-/opt/homebrew/bin/brew /usr/local/bin/brew}; do
  if [ -x "$candidate" ]; then BREW_PREFIX="$(dirname "$(dirname "$candidate")")"; break; fi
done
[ -n "$BREW_PREFIX" ] || BREW_PREFIX="$(brew --prefix 2>/dev/null || echo /usr/local)"
# Container-Werkzeuge (modules-mac/70-containers.sh): incus/colima für den Kern, nur wenn installiert.
HH_CT_BIN="${HH_CT_BIN:-/usr/local/lib/hydrahive2/containers/bin}"
CT_PATH=""
[ -d "$HH_CT_BIN" ] && CT_PATH="${HH_CT_BIN}:"
# Tailscale ohne App (modules-mac/80-tailscale.sh)
HH_TS_BIN="${HH_TS_BIN:-/usr/local/lib/hydrahive2/tailscale/bin}"
[ -d "$HH_TS_BIN" ] && CT_PATH="${CT_PATH}${HH_TS_BIN}:"

# JWT-Secret
SECRET_FILE="$HH_CONFIG_DIR/secret_key"
if ! priv test -f "$SECRET_FILE"; then
  log "Generiere JWT-Secret"
  python3 -c "import secrets; print(secrets.token_urlsafe(48))" | priv tee "$SECRET_FILE" > /dev/null
fi
hh_service_account && priv chown "$HH_USER" "$SECRET_FILE"
# Secrets NICHT in die plist: sie ist root:wheel 0644 und für jeden lokalen
# Nutzer lesbar (auch per `launchctl print`). HH_SECRET_KEY und
# HH_PG_MIRROR_DSN liest mac-backend-start.sh beim Start aus secret_key und
# pg_mirror.dsn (beide 0600). Reste aus alten Installationen aufräumen:
priv chmod 600 "$SECRET_FILE"
if priv test -f "$HH_CONFIG_DIR/pg_mirror.dsn"; then priv chmod 600 "$HH_CONFIG_DIR/pg_mirror.dsn"; fi
priv rm -f "$HH_CONFIG_DIR/.pg_dsn_tmp"

# HOME: eigenes Dienst-Konto → dessen Home (Caches); alter Weg wie bisher /Users/<Mac-Besitzer>.
SVC_HOME="/Users/${HH_USER}"
hh_service_account && SVC_HOME="$(hh_svc_home)"

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
        <string>/bin/bash</string>
        <string>${START_WRAPPER}</string>
        <string>${HH_REPO_DIR}/.venv/bin/uvicorn</string>
        <string>hydrahive.api.main:app</string>
        <string>--host</string>
        <string>${HH_HOST}</string>
        <string>--port</string>
        <string>${HH_PORT}</string>
        <string>--timeout-graceful-shutdown</string>
        <string>20</string>
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
        <key>HH_LOG_DIR</key>
        <string>/usr/local/var/log</string>
        <key>HOME</key>
        <string>${SVC_HOME}</string>
        <key>PATH</key>
        <string>${HH_REPO_DIR}/.venv/bin:${CT_PATH}${BREW_PREFIX}/opt/python@3.12/bin:${BREW_PREFIX}/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>COLIMA_HOME</key>
        <string>${HH_DATA_DIR}/colima</string>
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
