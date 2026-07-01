#!/usr/bin/env bash
# HydraHive2 — Server-zu-Server Voll-Klon per rsync.
#
# Wird vom root-oneshot-Service hydrahive2-migration.service ausgeführt, wenn der
# Core-Router die Trigger-Datei $HH_DATA_DIR/.migration_request geschrieben hat.
# Überträgt ALLE Daten (inkl. workspaces/, modules/, vms/, Plattenarchive) per
# rsync -aAX --delete über SSH auf einen frisch installierten HydraHive2-Zielserver.
#
# rsync ist inkrementell + resumierbar — bei 1,2 TB Pflicht. Zweiter Lauf
# überträgt nur das Delta.
#
# Auth: SSH-Passwort via sshpass -f (Secret-Datei). Passwort steht NIE in der
# Prozessliste und NIE im Log.
set -uo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_USER="${HH_USER:-hydrahive}"
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/etc/hydrahive2}"

TRIGGER="$HH_DATA_DIR/.migration_request"
SECRET="$HH_DATA_DIR/.migration_secret"
DONE_MARKER="$HH_DATA_DIR/.migration_done"

log()  { printf '\033[1;36m[hh2-migrate]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[hh2-migrate]\033[0m WARN: %s\n' "$*"; }

# Aufräumen: Secret immer löschen, Ergebnis in DONE_MARKER schreiben.
FINAL_RC=1
finish() {
    # Passwort-Datei restlos entfernen, egal wie wir hier landen.
    rm -f "$SECRET" 2>/dev/null || true
    printf '{"ok":%s,"finished_at":%s}\n' \
        "$([ "$FINAL_RC" -eq 0 ] && echo true || echo false)" \
        "$(date +%s)" > "$DONE_MARKER" 2>/dev/null || true
    if [ "$FINAL_RC" -eq 0 ]; then
        log "════════ Migration erfolgreich abgeschlossen ════════"
    else
        warn "════════ Migration fehlgeschlagen (rc=$FINAL_RC) ════════"
    fi
}
trap finish EXIT

err() { warn "$*"; FINAL_RC=1; exit 1; }

[ "$(id -u)" -eq 0 ] || err "migrate.sh muss als root laufen."

# ── Trigger + Secret einlesen ────────────────────────────────────────────────
[ -f "$TRIGGER" ] || err "Kein Migrations-Trigger gefunden ($TRIGGER)."
[ -f "$SECRET" ]  || err "Kein Passwort hinterlegt ($SECRET)."

# JSON-Felder ohne jq extrahieren (python3 ist auf HH2-Servern immer da).
read_field() {
    python3 -c "import json,sys;print(json.load(open('$TRIGGER')).get('$1',''))" 2>/dev/null
}
TARGET_HOST="$(read_field host)"
TARGET_PORT="$(read_field port)"
TARGET_USER="$(read_field ssh_user)"
BWLIMIT_KBPS="$(read_field bwlimit_kbps)"

[ -n "$TARGET_HOST" ] || err "Ziel-Host fehlt im Trigger."
[ -n "$TARGET_PORT" ] || TARGET_PORT=22
[ -n "$TARGET_USER" ] || TARGET_USER=root
[ -n "$BWLIMIT_KBPS" ] || BWLIMIT_KBPS=0

# Trigger jetzt entfernen → /status zeigt "läuft" nur noch über SECRET, das am
# Ende gelöscht wird. (Der Service hat den Trigger via ExecStartPre schon weg,
# aber doppelt hält besser falls manuell gestartet.)
rm -f "$TRIGGER" 2>/dev/null || true

log "Ziel: ${TARGET_USER}@${TARGET_HOST}:${TARGET_PORT}"
log "Quelle: $(hostname)"
[ "$BWLIMIT_KBPS" -gt 0 ] 2>/dev/null && log "Bandbreiten-Limit: ${BWLIMIT_KBPS} KB/s"

SSH_OPTS=(-p "$TARGET_PORT" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)
SSHPASS_CMD=(sshpass -f "$SECRET")
REMOTE="${TARGET_USER}@${TARGET_HOST}"

remote_ssh() { "${SSHPASS_CMD[@]}" ssh "${SSH_OPTS[@]}" "$REMOTE" "$@"; }

# ── [0] Preflight ────────────────────────────────────────────────────────────
log "[0/5] Preflight-Checks"
command -v rsync   >/dev/null || err "rsync auf Quellserver nicht gefunden."
command -v sshpass >/dev/null || err "sshpass auf Quellserver nicht gefunden."

if ! remote_ssh "echo ok" >/dev/null 2>&1; then
    err "SSH-Verbindung zu $REMOTE fehlgeschlagen (Host/Port/Passwort prüfen)."
fi
log "    SSH-Verbindung: OK"

remote_ssh "command -v rsync >/dev/null" \
    || err "rsync auf Ziel-Server nicht gefunden — dort installieren."
log "    rsync auf Ziel: OK"

remote_ssh "test -d $HH_CONFIG_DIR" \
    || err "$HH_CONFIG_DIR auf Ziel fehlt — HydraHive2 dort zuerst installieren."
log "    HydraHive2 auf Ziel installiert: OK"

# Freien Platz auf Ziel grob prüfen (KB) vs. Quell-Datenmenge.
SRC_KB="$(du -sk --one-file-system "$HH_DATA_DIR" 2>/dev/null | cut -f1)"
DST_AVAIL_KB="$(remote_ssh "df -Pk $HH_DATA_DIR | tail -1 | awk '{print \$4}'" 2>/dev/null)"
if [ -n "$SRC_KB" ] && [ -n "$DST_AVAIL_KB" ]; then
    log "    Quelle: $((SRC_KB/1024/1024)) GB  |  Ziel frei: $((DST_AVAIL_KB/1024/1024)) GB"
    if [ "$DST_AVAIL_KB" -lt "$SRC_KB" ]; then
        err "Zu wenig Platz auf Ziel ($((DST_AVAIL_KB/1024/1024)) GB frei, $((SRC_KB/1024/1024)) GB nötig)."
    fi
fi

# ── [1] Konsistenter DB-Snapshot ─────────────────────────────────────────────
log "[1/5] DB-Snapshot (WAL-safe via sqlite3 .backup)"
DB_SRC="$HH_DATA_DIR/sessions.db"
SNAP_DIR="$HH_DATA_DIR/.migration-dbsnap"
rm -rf "$SNAP_DIR"; mkdir -p "$SNAP_DIR"
if [ -f "$DB_SRC" ]; then
    if command -v sqlite3 >/dev/null; then
        sqlite3 "$DB_SRC" ".backup '$SNAP_DIR/sessions.db'" \
            && log "    Snapshot erstellt ($(du -h "$SNAP_DIR/sessions.db" | cut -f1))" \
            || warn "    sqlite3 .backup fehlgeschlagen — DB wird als Datei gesynct (evtl. WAL-inkonsistent)"
    else
        warn "    sqlite3 fehlt — DB wird als Datei gesynct"
    fi
fi

# ── [2] rsync-Ausschlüsse (regenerierbarer Ballast) ──────────────────────────
# Nutzdaten (Git-Repos, Code, Configs, Archive, VMs) bleiben ALLE drin.
EXCLUDES=(
    --exclude 'node_modules/'
    --exclude '.venv/'
    --exclude 'venv/'
    --exclude '__pycache__/'
    --exclude '.mypy_cache/'
    --exclude '.pytest_cache/'
    --exclude '.plugin-cache/'
    --exclude '.module-cache/'
    --exclude '.numba-cache/'
    --exclude 'gocache/'
    --exclude 'gomods/'
    --exclude '.migration-dbsnap/'
    --exclude '.migration_request'
    --exclude '.migration_secret'
    --exclude '.migration_done'
    --exclude '.backup-rollback-*'
    --exclude '.hh2-restore-*'
    --exclude 'memory_index.db'
    --exclude 'sessions.db-wal'
    --exclude 'sessions.db-shm'
)

RSYNC_OPTS=(-aAX --delete --numeric-ids --partial --info=progress2 --human-readable)
[ "$BWLIMIT_KBPS" -gt 0 ] 2>/dev/null && RSYNC_OPTS+=(--bwlimit="$BWLIMIT_KBPS")

RSH="sshpass -f $SECRET ssh -p $TARGET_PORT -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"

do_rsync() {
    local src="$1" dst="$2"; shift 2
    log "    rsync: $src → ${REMOTE}:$dst"
    rsync "${RSYNC_OPTS[@]}" "${EXCLUDES[@]}" "$@" \
        -e "$RSH" "$src" "${REMOTE}:$dst"
}

# ── [3] Ziel-Services stoppen (konsistenter Zustand) ─────────────────────────
log "[3/5] Ziel-Dienste stoppen"
remote_ssh "systemctl stop hydrahive2.service 2>/dev/null || true"

# ── [4] Übertragung ──────────────────────────────────────────────────────────
log "[4/5] Übertragung (rsync -aAX, inkrementell)"

# 4a: data_dir komplett (workspaces/, modules/, agents/, vms/, projects/, …).
#     Live-sessions.db ist excluded — Snapshot kommt separat.
do_rsync "$HH_DATA_DIR/" "$HH_DATA_DIR/" \
    || err "rsync von $HH_DATA_DIR fehlgeschlagen."

# 4b: DB-Snapshot an die richtige Stelle.
if [ -f "$SNAP_DIR/sessions.db" ]; then
    rsync "${RSYNC_OPTS[@]}" -e "$RSH" \
        "$SNAP_DIR/sessions.db" "${REMOTE}:$HH_DATA_DIR/sessions.db" \
        || warn "DB-Snapshot-Sync fehlgeschlagen."
fi

# 4c: config_dir (Secrets, users.json, llm.json, extensions).
do_rsync "$HH_CONFIG_DIR/" "$HH_CONFIG_DIR/" \
    || err "rsync von $HH_CONFIG_DIR fehlgeschlagen."

# ── [5] Ownership/Permissions auf Ziel korrigieren + Neustart ────────────────
log "[5/5] Ownership/Permissions + Ziel-Neustart"
remote_ssh "
    id $HH_USER >/dev/null 2>&1 && chown -R $HH_USER:$HH_USER $HH_DATA_DIR 2>/dev/null || true
    chown -R root:$HH_USER $HH_CONFIG_DIR 2>/dev/null || true
    chmod 750 $HH_CONFIG_DIR 2>/dev/null || true
    find $HH_CONFIG_DIR -type f -exec chmod 640 {} + 2>/dev/null || true
    find $HH_DATA_DIR -name 'memory_index.db' -delete 2>/dev/null || true
    systemctl start hydrahive2.service 2>/dev/null || true
" || warn "Nacharbeiten auf Ziel teilweise fehlgeschlagen (manuell prüfen)."

rm -rf "$SNAP_DIR" 2>/dev/null || true

log "Ziel-Server neu gestartet. Klon steht bereit."
FINAL_RC=0
exit 0
