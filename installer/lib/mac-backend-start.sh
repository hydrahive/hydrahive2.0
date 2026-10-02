#!/bin/bash
# Start-Wrapper für das HydraHive-Backend unter macOS (launchd).
#
# Früher standen HH_SECRET_KEY (signiert alle Logins) und der Postgres-Mirror-
# DSN samt Passwort als EnvironmentVariables in
# /Library/LaunchDaemons/io.hydrahive.backend.plist (root:wheel 0644) — lesbar
# für jeden lokalen Nutzer, auch über `launchctl print system/…`. launchd kennt
# kein EnvironmentFile wie systemd, deshalb liest dieser Wrapper die Werte beim
# Start aus $HH_CONFIG_DIR/secret_key und pg_mirror.dsn (beide 0600, gehören
# dem Dienstnutzer) und startet dann das eigentliche Programm.
#
# Aufruf (aus der plist): mac-backend-start.sh <programm> [argumente…]
set -euo pipefail

CONFIG_DIR="${HH_CONFIG_DIR:?HH_CONFIG_DIR fehlt}"
KEY_FILE="$CONFIG_DIR/secret_key"
DSN_FILE="$CONFIG_DIR/pg_mirror.dsn"

key="$(tr -d '\r\n' < "$KEY_FILE" 2>/dev/null || true)"
if [ -z "$key" ]; then
  echo "mac-backend-start: $KEY_FILE fehlt oder ist leer — Backend startet nicht" >&2
  exit 78  # EX_CONFIG
fi
export HH_SECRET_KEY="$key"

if [ -s "$DSN_FILE" ]; then
  export HH_PG_MIRROR_DSN="$(tr -d '\r\n' < "$DSN_FILE")"
else
  unset HH_PG_MIRROR_DSN
fi

exec "$@"
