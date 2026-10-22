#!/usr/bin/env bash
set -euo pipefail
log()  { printf "  · %s\n" "$*"; }
skip() { printf "  · (bereits vorhanden) %s\n" "$*"; }
# brew als Homebrew-Besitzer, psql als Dienst-Konto (Superuser der Datenbank) – lib/mac-roles.sh
# shellcheck source=../lib/mac-roles.sh
source "${INSTALLER_DIR:-$HH_REPO_DIR/installer}/lib/mac-roles.sh"
brew() { as_brew "$@"; }

eval "$(/usr/local/bin/brew shellenv zsh 2>/dev/null || /opt/homebrew/bin/brew shellenv zsh 2>/dev/null || true)"

DSN_FILE="${HH_CONFIG_DIR}/pg_mirror.dsn"
PG_DB="hydrahive_mirror"
PG_USER="hydrahive_mirror"
PLIST_FILE="$HH_CONFIG_DIR/pg_env.plist"

# PostgreSQL via brew
if ! brew list postgresql@16 &>/dev/null; then
  log "Installiere postgresql@16"
  brew install postgresql@16 --quiet
fi

# pgvector aus Source für postgresql@16 (brew pgvector linkt gegen neuere PG-Version)
PG_EXT_DIR="$(brew --prefix postgresql@16)/share/postgresql@16/extension"
if [ ! -f "$PG_EXT_DIR/vector.control" ]; then
  log "Baue pgvector aus Source für postgresql@16"
  TMP=$(mktemp -d)
  git clone --quiet --depth 1 https://github.com/pgvector/pgvector.git "$TMP/pgvector"
  PG_CONFIG="$(brew --prefix postgresql@16)/bin/pg_config" make -C "$TMP/pgvector" >/dev/null
  PG_CONFIG="$(brew --prefix postgresql@16)/bin/pg_config" make -C "$TMP/pgvector" install >/dev/null
  rm -rf "$TMP"
fi

# PostgreSQL starten – als LaunchDaemon, damit die Datenbank wie das Backend schon beim
# Hochfahren läuft – nicht erst nach der Anmeldung wie früher mit dem brew-services-Agenten.
bash "${INSTALLER_DIR:-$HH_REPO_DIR/installer}/lib/mac-postgres-daemon.sh"

# postgresql@16 ist keg-only (nicht nach $(brew --prefix)/bin verlinkt). Der Pfad
# hängt von der Mac-Art ab: /usr/local (Intel) oder /opt/homebrew (Apple Silicon).
export PATH="$(brew --prefix postgresql@16)/bin:$PATH"

# DB + User anlegen
# psql über TCP (wie AgentLink): als Dienst-Konto, der Superuser-Rolle der Datenbank.
PSQL_BIN="$(brew --prefix postgresql@16)/bin/psql"
psql() { ( cd /tmp && as_svc "$PSQL_BIN" -h 127.0.0.1 "$@" ); }

if priv test -f "$DSN_FILE"; then
  skip "pg_mirror.dsn bereits vorhanden"
else
  log "Lege DB-User + Datenbank an"
  PG_PASS=$(openssl rand -hex 16)

  psql postgres -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$PG_USER') THEN CREATE USER $PG_USER WITH PASSWORD '$PG_PASS'; END IF; END \$\$;" 2>/dev/null || true
  psql postgres -c "CREATE DATABASE $PG_DB OWNER $PG_USER;" 2>/dev/null || true
  psql "$PG_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || log "pgvector-Extension — nach Neustart nochmal versuchen"

  PG_DSN="postgresql://${PG_USER}:${PG_PASS}@127.0.0.1:5432/${PG_DB}"
  ( umask 077; echo "$PG_DSN" | priv tee "$DSN_FILE" > /dev/null )
  log "DSN gespeichert: $DSN_FILE"
fi

# Den DSN liest der Start-Wrapper (installer/lib/mac-backend-start.sh) direkt
# aus pg_mirror.dsn — kein Zwischenfile, nichts davon in der launchd-plist.
priv chmod 600 "$DSN_FILE"
priv chown "$HH_USER" "$DSN_FILE"
log "PostgreSQL bereit (DB: $PG_DB)"
