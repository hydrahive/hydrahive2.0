#!/usr/bin/env bash
# Installiert PostgreSQL + pgvector für den HydraHive2 Datamining-Mirror. Idempotent.
set -euo pipefail

log()  { printf "  · %s\n" "$*"; }
skip() { printf "  · (bereits vorhanden) %s\n" "$*"; }

DSN_FILE="${HH_CONFIG_DIR}/pg_mirror.dsn"
DROPIN_DIR="/etc/systemd/system/hydrahive2.service.d"
DROPIN_FILE="$DROPIN_DIR/pg-mirror.conf"
PG_DB="hydrahive_mirror"
PG_USER="hydrahive_mirror"

# ---------------------------------------------------------------- PostgreSQL apt
if ! command -v psql >/dev/null 2>&1; then
  log "Installiere postgresql + postgresql-contrib"
  DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-contrib >/dev/null
fi

# pgvector — Paketname hängt von der PG-Version ab (postgresql-16-pgvector auf 24.04)
PG_VER=$(pg_lsclusters --no-header 2>/dev/null | awk '{print $1; exit}' || echo "16")
if ! dpkg -l "postgresql-${PG_VER}-pgvector" >/dev/null 2>&1; then
  log "Installiere postgresql-${PG_VER}-pgvector"
  DEBIAN_FRONTEND=noninteractive apt-get install -y "postgresql-${PG_VER}-pgvector" >/dev/null \
    || log "pgvector-Paket nicht via apt verfügbar — Extension manuell einrichten"
fi

systemctl enable postgresql --quiet
systemctl start postgresql

# ---------------------------------------------------------------- DB + User
if [ -f "$DSN_FILE" ]; then
  skip "pg_mirror.dsn existiert bereits — überspringe DB-Einrichtung"
  PG_DSN=$(cat "$DSN_FILE")
else
  log "Lege Datenbankuser + Datenbank an"
  PG_PASS=$(openssl rand -hex 16)

  sudo -u postgres psql -v ON_ERROR_STOP=0 <<SQL 2>/dev/null || true
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$PG_USER') THEN
    CREATE USER $PG_USER WITH PASSWORD '$PG_PASS';
  END IF;
END
\$\$;
SQL

  sudo -u postgres psql -v ON_ERROR_STOP=0 -c \
    "CREATE DATABASE $PG_DB OWNER $PG_USER;" 2>/dev/null || true

  sudo -u postgres psql -d "$PG_DB" -v ON_ERROR_STOP=0 -c \
    "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null \
    || log "pgvector-Extension nicht installiert — nach manuellem apt-Install nochmal ausführen"

  PG_DSN="postgresql://${PG_USER}:${PG_PASS}@127.0.0.1:5432/${PG_DB}"
  echo "$PG_DSN" > "$DSN_FILE"
  chmod 600 "$DSN_FILE"
  chown "root:${HH_USER:-hydrahive}" "$DSN_FILE"
  log "DSN gespeichert: $DSN_FILE"
fi

# ---------------------------------------------------------------- systemd Drop-in
mkdir -p "$DROPIN_DIR"
if [ ! -f "$DROPIN_FILE" ] || ! grep -q "HH_PG_MIRROR_DSN" "$DROPIN_FILE"; then
  log "systemd Drop-in schreiben: $DROPIN_FILE"
  cat > "$DROPIN_FILE" <<EOF
[Service]
Environment=HH_PG_MIRROR_DSN=$PG_DSN
EOF
  chmod 644 "$DROPIN_FILE"
  systemctl daemon-reload
fi

log "PostgreSQL Datamining-Mirror bereit (DB: $PG_DB, User: $PG_USER)"
