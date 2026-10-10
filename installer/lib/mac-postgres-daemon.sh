#!/bin/bash
# PostgreSQL (Homebrew postgresql@16) als LaunchDaemon unter dem HydraHive-Nutzer.
#
# Früher startete 48-postgres.sh die Datenbank mit `brew services start`. Als
# normaler Nutzer legt das einen LaunchAgent an (~/Library/LaunchAgents), der
# erst nach der Anmeldung dieses Nutzers läuft. Das Backend ist aber ein
# LaunchDaemon und startet schon beim Hochfahren: nach jedem Neustart lief
# HydraHive ohne Datamining, bis sich jemand anmeldete.
#
# Jetzt: eigener LaunchDaemon io.hydrahive.postgres mit UserName=$HH_USER
# (dem Besitzer des Datenverzeichnisses), gleiche Parameter wie der
# Homebrew-Service der Formel. Der brew-services-Agent wird abgemeldet, damit
# nicht zwei Postmaster dasselbe Datenverzeichnis wollen.
#
# Läuft aus 48-postgres.sh (als Nutzer, mit sudo) und aus update-mac.sh (als
# root, Umbau bestehender Installationen). Idempotent.
# Env: HH_USER (Pflicht), HH_PG_PLIST (Test), HH_PG_WAIT (Sekunden, Default 30).
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

HH_USER="${HH_USER:?HH_USER fehlt}"
PLIST="${HH_PG_PLIST:-/Library/LaunchDaemons/io.hydrahive.postgres.plist}"
LABEL="io.hydrahive.postgres"
AGENT_LABEL="homebrew.mxcl.postgresql@16"
WAIT="${HH_PG_WAIT:-30}"

as_root() { [ "$(id -u)" -eq 0 ]; }
# Homebrew verweigert root – als root deshalb über den HydraHive-Nutzer aufrufen.
run_brew() { if as_root; then sudo -u "$HH_USER" brew "$@"; else brew "$@"; fi; }
priv() { if as_root; then "$@"; else sudo "$@"; fi; }

eval "$(/usr/local/bin/brew shellenv zsh 2>/dev/null || /opt/homebrew/bin/brew shellenv zsh 2>/dev/null || true)"

BREW_PREFIX="$(run_brew --prefix)"
PG_PREFIX="$(run_brew --prefix postgresql@16)"
DATA_DIR="$BREW_PREFIX/var/postgresql@16"
PG_LOG="$BREW_PREFIX/var/log/postgresql@16.log"

# 0) Datenverzeichnis muss dem Nutzer gehören, unter dem der Daemon läuft (postgres verweigert
#    sonst den Start). Bei abweichendem Besitzer abbrechen statt still umzustellen.
if [ -d "$DATA_DIR" ]; then
  # BSD-stat (macOS) vs. GNU-stat (Tests unter Linux): `stat -f` heißt bei GNU etwas anderes.
  if [ "$(uname)" = "Darwin" ]; then owner="$(stat -f %Su "$DATA_DIR")"; else owner="$(stat -c %U "$DATA_DIR")"; fi
  if [ -n "$owner" ] && [ "$owner" != "$HH_USER" ]; then
    log "Datenverzeichnis $DATA_DIR gehört '$owner', nicht '$HH_USER' – Umstellung abgebrochen"
    exit 1
  fi
fi

# 1) brew-services-Agent abmelden (startet sonst bei der Anmeldung einen zweiten Postmaster).
log "brew-services-Agent für postgresql@16 abmelden (falls vorhanden)"
if as_root; then
  uid="$(id -u "$HH_USER")"
  launchctl bootout "gui/$uid/$AGENT_LABEL" >/dev/null 2>&1 || true
  sudo -u "$HH_USER" brew services stop postgresql@16 >/dev/null 2>&1 || true
else
  brew services stop postgresql@16 >/dev/null 2>&1 || true
fi
AGENT_HOME="$(dscl . -read "/Users/$HH_USER" NFSHomeDirectory 2>/dev/null | awk '{print $2}' || true)"
[ -n "$AGENT_HOME" ] || AGENT_HOME="/Users/$HH_USER"
priv rm -f "$AGENT_HOME/Library/LaunchAgents/$AGENT_LABEL.plist"

# 2) LaunchDaemon schreiben (Parameter wie der Service-Block der Homebrew-Formel).
log "Schreibe $PLIST"
priv tee "$PLIST" > /dev/null <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PG_PREFIX}/bin/postgres</string>
        <string>-D</string>
        <string>${DATA_DIR}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>LC_ALL</key>
        <string>en_US.UTF-8</string>
    </dict>
    <key>UserName</key>
    <string>${HH_USER}</string>
    <key>WorkingDirectory</key>
    <string>${BREW_PREFIX}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ExitTimeOut</key>
    <integer>120</integer>
    <key>StandardOutPath</key>
    <string>${PG_LOG}</string>
    <key>StandardErrorPath</key>
    <string>${PG_LOG}</string>
</dict>
</plist>
EOF
priv chmod 644 "$PLIST"

# 3) (Neu) laden und warten, bis die Datenbank Verbindungen annimmt.
priv launchctl unload "$PLIST" >/dev/null 2>&1 || true
priv launchctl load "$PLIST"
for ((i = 0; i < WAIT; i++)); do
  if "$PG_PREFIX/bin/pg_isready" -h 127.0.0.1 -q 2>/dev/null; then
    log "PostgreSQL läuft als LaunchDaemon ($LABEL, Nutzer $HH_USER)"
    exit 0
  fi
  sleep 1
done
log "PostgreSQL antwortet nach ${WAIT} s nicht – siehe $PG_LOG"
exit 1
