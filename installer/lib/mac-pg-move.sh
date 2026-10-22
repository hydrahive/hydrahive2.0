#!/bin/bash
# macOS: Datenbank vom alten Nutzer (Homebrew-Datenordner) zum Dienst-Konto umziehen (Etappe 3,
# docs/plans/mac-service-user.md). Aufruf aus mac-migrate-service-user.sh (root).
#
# Dump als alter Superuser (läuft noch) → alten Dienst anhalten → warten, bis Port 5432 frei ist → neuer Datenordner
# + Dienst als Konto (mac-postgres-daemon.sh) → Rolle des alten Nutzers anlegen → Import → Datenbanken zählen.
# Warten auf den Port: Startet der neue Postmaster, solange der alte noch herunterfährt, bekommt er nur ::1 und
# nicht 127.0.0.1 – AgentLink/Backend erreichen ihn dann nicht (Befund 22.10.2026).
# Der Homebrew-Datenordner bleibt unangetastet liegen (Rückweg). Merker $DATA/.hh-imported: nicht doppelt importieren.
# Env: HH_OLD_USER, HH_USER (Konto), HH_PG_DUMP (Zieldatei); Tests: HH_PG_DATA, HH_PG_PORT_WAIT, HH_PG_PLIST.
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

OLD="${HH_OLD_USER:?HH_OLD_USER fehlt}"
DUMP="${HH_PG_DUMP:?HH_PG_DUMP fehlt}"
NEW_DATA="${HH_PG_DATA:-/usr/local/var/hydrahive2/postgres}"
PORT_WAIT="${HH_PG_PORT_WAIT:-60}"
LIB="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=mac-roles.sh
source "$LIB/mac-roles.sh"
cd /tmp

if [ -f "$NEW_DATA/.hh-imported" ]; then
  log "Datenbank ist schon umgezogen"
  exit 0
fi
PG="$(as_brew --prefix postgresql@16)/bin"
count_dbs() { "$@" "$PG/psql" -h 127.0.0.1 -d postgres -tAc "SELECT count(*) FROM pg_database WHERE NOT datistemplate"; }

# 1) Sicherung der alten Datenbank (alter Dienst läuft noch)
before="$(count_dbs sudo -u "$OLD")" || { echo "alte Datenbank nicht erreichbar" >&2; exit 1; }
( umask 077; sudo -u "$OLD" "$PG/pg_dumpall" -h 127.0.0.1 > "$DUMP" ) || { echo "pg_dumpall fehlgeschlagen" >&2; exit 1; }
chmod 600 "$DUMP"
log "Alte Datenbank gesichert ($before Datenbanken, $DUMP)"

# 2) Alten Dienst anhalten, warten bis der Port frei ist
launchctl bootout system/io.hydrahive.postgres 2>/dev/null || true
free=""
for ((i = 0; i < PORT_WAIT; i++)); do
  if ! lsof -nP -iTCP:5432 -sTCP:LISTEN >/dev/null 2>&1; then free=1; break; fi
  sleep 1
done
[ -n "$free" ] || { echo "Port 5432 bleibt belegt – alte Datenbank läuft noch" >&2; exit 1; }

# 3) Neuer Datenordner + Dienst als Konto. Ein Ordner ohne Fertig-Merker stammt von einem abgebrochenen Versuch:
#    beiseite (nicht löschen), sonst würde in eine halb gefüllte Datenbank doppelt importiert.
if [ -d "$NEW_DATA" ]; then
  aside="$NEW_DATA.unfertig-$(date +%Y%m%d-%H%M%S)"
  log "Rest eines früheren Versuchs nach $aside"
  mv "$NEW_DATA" "$aside"
fi
bash "$LIB/mac-postgres-daemon.sh" || { echo "neue Datenbank startet nicht" >&2; exit 1; }
[ -d "$NEW_DATA" ] || { echo "neuer Datenordner fehlt ($NEW_DATA)" >&2; exit 1; }

# 4) Rolle des alten Nutzers (Eigentümer im Dump), dann Import. Ohne ON_ERROR_STOP: „Rolle existiert schon“ ist normal.
as_svc "$PG/psql" -h 127.0.0.1 -d postgres -q -c \
  "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$OLD') THEN CREATE ROLE \"$OLD\" LOGIN; END IF; END \$\$;" \
  < /dev/null || { echo "Rolle $OLD konnte nicht angelegt werden" >&2; exit 1; }
# Import aus einer eigenen Kopie: die Sicherung liegt in einem root-Ordner (0700), den das Konto nicht betreten darf
# (Befund 22.10.2026, .186: „Permission denied“ auf den Dump).
IMPORT="$(mktemp /tmp/hh-pg-import.XXXXXX)"
trap 'rm -f "$IMPORT"' EXIT
cat "$DUMP" > "$IMPORT"
chown "$HH_USER" "$IMPORT"
chmod 600 "$IMPORT"
as_svc "$PG/psql" -h 127.0.0.1 -d postgres -q -f "$IMPORT" < /dev/null > /dev/null 2>&1 \
  || { echo "Import fehlgeschlagen" >&2; exit 1; }
rm -f "$IMPORT"
after="$(count_dbs as_svc)" || { echo "neue Datenbank nicht erreichbar" >&2; exit 1; }
if [ "$after" != "$before" ]; then
  echo "Import unvollständig: $after statt $before Datenbanken (Sicherung: $DUMP)" >&2
  exit 1
fi
touch "$NEW_DATA/.hh-imported"
chown "$HH_USER" "$NEW_DATA/.hh-imported"
log "Datenbank umgezogen ($after Datenbanken, gehört $HH_USER)"
