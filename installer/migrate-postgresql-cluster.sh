#!/usr/bin/env bash
# Gesicherte, explizite PostgreSQL-Major-Migration nach einem Ubuntu-Upgrade.
# Standard: 16/main -> 18/main. Der alte Cluster wird NIE gelöscht.
set -Eeuo pipefail

export PATH=/usr/sbin:/usr/bin:/sbin:/bin
export LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive
umask 077

OLD_VERSION=16
TARGET_VERSION=18
CLUSTER=main
CONFIRMED=0
BACKUP_DIR=/var/backups/hydrahive2

log() { printf '\033[1;36m[hh2-pg-upgrade]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[hh2-pg-upgrade]\033[0m %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'EOF'
Verwendung:
  sudo ./installer/migrate-postgresql-cluster.sh --yes \
    [--old-version 16] [--target-version 18] [--cluster main]

Das Skript erstellt zuerst ein geprüftes pg_dumpall-Backup, migriert dann mit
pg_upgradecluster (sicheres dump/restore-Verfahren) und behält den alten Cluster
als gestoppten Rollback-Punkt. Es löscht niemals Cluster oder Backups.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --yes) CONFIRMED=1; shift ;;
    --old-version) [ "$#" -ge 2 ] || err "Wert für --old-version fehlt"; OLD_VERSION="$2"; shift 2 ;;
    --target-version) [ "$#" -ge 2 ] || err "Wert für --target-version fehlt"; TARGET_VERSION="$2"; shift 2 ;;
    --cluster) [ "$#" -ge 2 ] || err "Wert für --cluster fehlt"; CLUSTER="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) err "Unbekanntes Argument: $1" ;;
  esac
done

[ "$CONFIRMED" -eq 1 ] || err "Explizite Bestätigung fehlt. Nach geprüftem Backup mit --yes aufrufen."
[ "$(id -u)" -eq 0 ] || err "Bitte als root/sudo ausführen."
[[ "$OLD_VERSION" =~ ^[0-9]+$ ]] || err "Ungültige alte PostgreSQL-Version: $OLD_VERSION"
[[ "$TARGET_VERSION" =~ ^[0-9]+$ ]] || err "Ungültige Zielversion: $TARGET_VERSION"
[[ "$CLUSTER" =~ ^[A-Za-z0-9_-]+$ ]] || err "Ungültiger Clustername: $CLUSTER"
[ "$OLD_VERSION" -lt "$TARGET_VERSION" ] || err "Zielversion muss größer als alte Version sein."

exec 9>/run/hydrahive2-postgresql-upgrade.lock
flock -n 9 || err "Eine PostgreSQL-Migration läuft bereits."

cluster_row() {
  pg_lsclusters --no-header 2>/dev/null \
    | awk -v version="$1" -v name="$2" '$1 == version && $2 == name {print; exit}'
}
field() { awk -v number="$1" '{print $number}'; }
run_pg() { /usr/sbin/runuser -u postgres -- "$@"; }

OLD_ROW="$(cluster_row "$OLD_VERSION" "$CLUSTER")"
TARGET_ROW="$(cluster_row "$TARGET_VERSION" "$CLUSTER")"

# Idempotenz: Nach erfolgreicher Migration bleibt der alte Cluster gestoppt und
# der Zielcluster online. Ein erneuter Aufruf darf weder Backup noch Migration
# unnötig wiederholen.
if [ -n "$TARGET_ROW" ]; then
  TARGET_STATUS="$(printf '%s\n' "$TARGET_ROW" | field 4)"
  OLD_STATUS="$(printf '%s\n' "$OLD_ROW" | field 4)"
  if [ "$TARGET_STATUS" = "online" ] && { [ -z "$OLD_ROW" ] || [ "$OLD_STATUS" = "down" ]; }; then
    log "PostgreSQL $TARGET_VERSION/$CLUSTER ist bereits online; keine Migration nötig."
    systemctl start hydrahive2.service agentlink.service 2>/dev/null || true
    exit 0
  fi
  err "Zielcluster $TARGET_VERSION/$CLUSTER existiert bereits in einem uneindeutigen Zustand. Nichts wird automatisch gelöscht."
fi

[ -n "$OLD_ROW" ] || err "Quellcluster $OLD_VERSION/$CLUSTER wurde nicht gefunden."
OLD_PORT="$(printf '%s\n' "$OLD_ROW" | field 3)"
OLD_STATUS="$(printf '%s\n' "$OLD_ROW" | field 4)"
OLD_OWNER="$(printf '%s\n' "$OLD_ROW" | field 5)"
OLD_DATA_DIR="$(printf '%s\n' "$OLD_ROW" | field 6)"
[ "$OLD_OWNER" = "postgres" ] || err "Unerwarteter Cluster-Owner: $OLD_OWNER"
[ -d "$OLD_DATA_DIR" ] || err "Datenverzeichnis fehlt: $OLD_DATA_DIR"

log "Quelle: PostgreSQL $OLD_VERSION/$CLUSTER ($OLD_STATUS, Port $OLD_PORT)"
log "Ziel:  PostgreSQL $TARGET_VERSION/$CLUSTER"

# Für dump/restore werden alter Cluster, neuer Cluster und ein externes
# logisches Backup gleichzeitig benötigt. 3x Quelldaten + 1 GiB Reserve ist
# konservativ und stoppt lieber früh als während der Migration.
DATA_BYTES="$(du -sb -- "$OLD_DATA_DIR" | awk '{print $1}')"
AVAILABLE_BYTES="$(df --output=avail -B1 /var/lib/postgresql | tail -1 | tr -d ' ')"
REQUIRED_BYTES=$((DATA_BYTES * 3 + 1073741824))
[ "$AVAILABLE_BYTES" -ge "$REQUIRED_BYTES" ] || err \
  "Zu wenig freier Speicher: verfügbar=$AVAILABLE_BYTES, benötigt mindestens=$REQUIRED_BYTES Bytes."

log "Installiere Zielserver und Erweiterungen"
apt-get update
apt-get install -y -- \
  "postgresql-${TARGET_VERSION}" \
  "postgresql-${TARGET_VERSION}-pgvector"

# pg_upgradecluster --check stellt sicher, dass alle Pakete/Extensions der alten
# Major-Version auch für die Zielversion bereitstehen.
log "Prüfe Erweiterungen und Upgrade-Fähigkeit"
pg_upgradecluster --check -v "$TARGET_VERSION" "$OLD_VERSION" "$CLUSTER"

if [ "$OLD_STATUS" != "online" ]; then
  log "Starte Quellcluster für das logische Backup"
  pg_ctlcluster "$OLD_VERSION" "$CLUSTER" start
fi

mkdir -p -- "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)-$$"
BACKUP_FILE="$BACKUP_DIR/postgresql-${OLD_VERSION}-${CLUSTER}-before-${TARGET_VERSION}-${STAMP}.sql.gz"
BACKUP_TMP="${BACKUP_FILE}.tmp"
trap 'rm -f -- "${BACKUP_TMP:-}"; printf "\n[hh2-pg-upgrade] FEHLER — alter Cluster und Backup werden nicht gelöscht.\n" >&2' ERR

log "Erstelle logisches Vollbackup: $BACKUP_FILE"
run_pg pg_dumpall | gzip -9 > "$BACKUP_TMP"
gzip -t "$BACKUP_TMP"
mv -- "$BACKUP_TMP" "$BACKUP_FILE"
chmod 600 "$BACKUP_FILE"
sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"
chmod 600 "${BACKUP_FILE}.sha256"

log "Stoppe schreibende HydraHive-Dienste"
systemctl stop hydrahive2.service agentlink.service 2>/dev/null || true

log "Migriere PostgreSQL $OLD_VERSION/$CLUSTER -> $TARGET_VERSION/$CLUSTER (Methode: dump)"
pg_upgradecluster -v "$TARGET_VERSION" --method=dump "$OLD_VERSION" "$CLUSTER"

NEW_ROW="$(cluster_row "$TARGET_VERSION" "$CLUSTER")"
[ -n "$NEW_ROW" ] || err "Zielcluster wurde nach der Migration nicht gefunden."
NEW_PORT="$(printf '%s\n' "$NEW_ROW" | field 3)"
NEW_STATUS="$(printf '%s\n' "$NEW_ROW" | field 4)"
[ "$NEW_STATUS" = "online" ] || err "Zielcluster ist nicht online: $NEW_STATUS"
[ "$NEW_PORT" = "$OLD_PORT" ] || err "Zielcluster hört auf Port $NEW_PORT statt $OLD_PORT"

# glibc 2.39 -> 2.43 ändert die Collation-Version. Erst alle Indizes mit der
# neuen libc neu bauen, danach die Metadaten-Version jeder DB aktualisieren.
log "Baue Indizes für die neue Collation-Version neu"
run_pg reindexdb --cluster "$TARGET_VERSION/$CLUSTER" --all
log "Aktualisiere Collation-Metadaten"
run_pg psql --cluster "$TARGET_VERSION/$CLUSTER" -d postgres -Atc \
  "SELECT format('ALTER DATABASE %I REFRESH COLLATION VERSION;', datname) FROM pg_database" \
  | run_pg psql --cluster "$TARGET_VERSION/$CLUSTER" -d postgres

log "Verifiziere Datenbanken und vector-Erweiterung"
run_pg psql --cluster "$TARGET_VERSION/$CLUSTER" -d postgres -v ON_ERROR_STOP=1 -Atc \
  "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY 1"
VECTOR_COUNT="$(run_pg psql --cluster "$TARGET_VERSION/$CLUSTER" -d hydrahive_mirror -Atc \
  "SELECT count(*) FROM pg_extension WHERE extname = 'vector'" 2>/dev/null || echo 0)"
[ "$VECTOR_COUNT" = "1" ] || err "vector-Erweiterung fehlt in hydrahive_mirror."

log "Starte HydraHive-Dienste"
systemctl start hydrahive2.service agentlink.service

OLD_AFTER="$(cluster_row "$OLD_VERSION" "$CLUSTER")"
OLD_AFTER_PORT="$(printf '%s\n' "$OLD_AFTER" | field 3)"
OLD_AFTER_STATUS="$(printf '%s\n' "$OLD_AFTER" | field 4)"
[ "$OLD_AFTER_STATUS" = "down" ] || err "Alter Cluster ist unerwartet nicht gestoppt: $OLD_AFTER_STATUS"
[ "$OLD_AFTER_PORT" != "$OLD_PORT" ] || err "Alter Cluster belegt weiterhin den Produktivport $OLD_PORT."

trap - ERR
log "Migration erfolgreich. Backup: $BACKUP_FILE"
log "Alter Cluster bleibt als Rollback-Punkt erhalten: $OLD_VERSION/$CLUSTER (down)."
cat <<EOF

Rollback (nur falls die Abnahme fehlschlägt, vorher Dienste stoppen):
  systemctl stop hydrahive2 agentlink
  pg_ctlcluster $TARGET_VERSION $CLUSTER stop
  pg_conftool $TARGET_VERSION $CLUSTER set port $OLD_AFTER_PORT
  pg_conftool $OLD_VERSION $CLUSTER set port $OLD_PORT
  pg_ctlcluster $OLD_VERSION $CLUSTER start
  systemctl start hydrahive2 agentlink

Den alten Cluster erst nach erfolgreicher Abnahme und separatem Backup manuell
entfernen. Dieses Skript führt bewusst kein pg_dropcluster aus.
EOF
