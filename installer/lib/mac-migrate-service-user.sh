#!/bin/bash
# macOS: bestehende Installation auf das eigene Dienst-Konto _hydrahive umziehen (Etappe 3,
# docs/plans/mac-service-user.md). Läuft als root aus update-mac.sh, einmalig (Merker HH_SERVICE_USER in install.conf).
#
# Warum: Ab macOS 15 sperrt „Lokales Netzwerk“ alle Programme des am Bildschirm angemeldeten Nutzers, auch als
# LaunchDaemon. Bisher lief HydraHive als Mac-Besitzer → Portfreigaben, Kopplung im LAN usw. kaputt.
#
# Reihenfolge: Sicherung → Konto → Dienste anhalten → Besitz → PostgreSQL → Dienst-Dateien neu → Prüfung → Merker.
# Der Merker kommt erst ganz am Ende: bricht etwas ab, versucht das nächste Update es erneut (alle Schritte
# vertragen eine Wiederholung). Abschalten: HH_SERVICE_ACCOUNT=no (Umgebung oder install.conf).
#
# Env: HH_USER (alter Dienst-Nutzer = Mac-Besitzer), HH_REPO_DIR, HH_DATA_DIR, HH_CONFIG_DIR; für Tests:
# HH_LOG_DIR, HH_HL_DIR, HH_HL_CONFIG_DIR, HH_TS_BIN, HH_BACKUP_ROOT, HH_MIGRATE_WAIT, HH_COLIMA_STOP.
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

OLD="${HH_USER:?HH_USER fehlt}"
HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
HH_LOG_DIR="${HH_LOG_DIR:-/usr/local/var/log}"
PLIST_DIR="${HH_PLIST_DIR:-/Library/LaunchDaemons}"
HL_DIR="${HH_HL_DIR:-/opt/hydralink}"
HL_CONFIG_DIR="${HH_HL_CONFIG_DIR:-/usr/local/etc/hydralink}"
TS_BIN="${HH_TS_BIN:-/usr/local/lib/hydrahive2/tailscale/bin}"
BACKUP_ROOT="${HH_BACKUP_ROOT:-/usr/local/var}"
WAIT="${HH_MIGRATE_WAIT:-60}"
CONF="$HH_CONFIG_DIR/install.conf"
LIB="$HH_REPO_DIR/installer/lib"
MODS="$HH_REPO_DIR/installer/modules-mac"

[ "${HH_SERVICE_ACCOUNT:-}" = "no" ] && exit 0
grep -q '^HH_SERVICE_ACCOUNT=no' "$CONF" 2>/dev/null && exit 0
grep -q '^HH_SERVICE_USER=' "$CONF" 2>/dev/null && exit 0
if [ -z "$OLD" ] || [ "$OLD" = "root" ] || [ "${OLD#_}" != "$OLD" ]; then
  echo "Umzug abgebrochen: alter Dienst-Nutzer '$OLD' ist kein Mac-Nutzer" >&2
  exit 1
fi

# Homebrew bleibt beim alten Nutzer (Mac-Besitzer); HydraHive bekommt das neue Konto.
HH_BREW_USER="${HH_BREW_USER:-$OLD}"
SVC="$(HH_USER="$OLD" bash "$LIB/mac-service-user.sh" | tail -1)"
[ -n "$SVC" ] || { echo "Dienst-Konto konnte nicht angelegt werden" >&2; exit 1; }
export HH_BREW_USER
HH_USER="$SVC"
# shellcheck source=mac-roles.sh
source "$LIB/mac-roles.sh"
cd /tmp

# --- 1) Sicherung (vor jedem Eingriff) ---------------------------------------------------------------------------
BACKUP="$BACKUP_ROOT/hydrahive2-backup-$(date +%Y%m%d-%H%M%S)"
log "Sicherung nach $BACKUP"
mkdir -p "$BACKUP"
chmod 700 "$BACKUP"
cp -Rp "$HH_CONFIG_DIR" "$BACKUP/etc"
mkdir -p "$BACKUP/plists"
for f in "$PLIST_DIR"/io.hydrahive.*.plist; do [ -f "$f" ] && cp -p "$f" "$BACKUP/plists/"; done
if [ -f "$HH_DATA_DIR/sessions.db" ]; then
  sqlite3 "$HH_DATA_DIR/sessions.db" ".backup $BACKUP/sessions.db"
fi
PG_DUMP=""
if [ -s "$HH_CONFIG_DIR/pg_mirror.dsn" ]; then
  PG_DUMP="$BACKUP/postgres-all.sql"
fi
ROLLBACK=""
fail() {
  echo "Umzug auf das Dienst-Konto abgebrochen: $* – Sicherung: $BACKUP. Das nächste Update versucht es erneut." >&2
  if [ -n "$ROLLBACK" ]; then
    HH_OLD_USER="$OLD" HH_SVC_USER="$SVC" HH_BACKUP="$BACKUP" HH_PLIST_DIR="$PLIST_DIR" HH_REPO_DIR="$HH_REPO_DIR" \
      HH_DATA_DIR="$HH_DATA_DIR" HH_CONFIG_DIR="$HH_CONFIG_DIR" HH_HL_DIR="$HL_DIR" HH_HL_CONFIG_DIR="$HL_CONFIG_DIR" \
      HH_LOG_DIR="$HH_LOG_DIR" bash "$LIB/mac-migrate-rollback.sh" >&2 || true
  fi
  exit 1
}

# --- 2) Dienste anhalten (root-Dienste wie nginx, tailscaled, update laufen weiter) -------------------------------
log "Dienste anhalten"
ROLLBACK=1   # ab hier bei Abbruch alten Stand wiederherstellen
for label in backend agentlink agentlink-frontend voice-stt voice-tts colima; do
  launchctl bootout "system/io.hydrahive.$label" 2>/dev/null || true
done
# VM sauber herunterfahren (gehört noch dem alten Nutzer); sonst wäre die Platte beim Besitzwechsel in Benutzung.
if [ -z "${HH_COLIMA_STOP:-}" ] && [ -x /usr/local/lib/hydrahive2/containers/bin/colima ]; then
  sudo -u "$OLD" env "COLIMA_HOME=$HH_DATA_DIR/colima" "PATH=/usr/local/lib/hydrahive2/containers/bin:/usr/bin:/bin" \
    colima stop hydrahive >/dev/null 2>&1 || true
fi

# --- 3) Besitz übertragen ----------------------------------------------------------------------------------------
log "Dateien gehören jetzt $SVC"
for d in "$HH_REPO_DIR" "$HH_DATA_DIR" "$HH_CONFIG_DIR" "$HL_DIR" "$HL_CONFIG_DIR"; do
  [ -e "$d" ] && chown -R "$SVC" "$d"
done
# Tailscale-Schlüssel und Voice-Programme gehören root – zurückstellen (chown -R oben hat sie mitgenommen).
[ -d "$HH_DATA_DIR/tailscale" ] && chown -R root "$HH_DATA_DIR/tailscale"
# Den Log-Ordner nicht übernehmen (auf Intel gehört er Homebrew) – nur die Dateien der Dienste.
chmod +a "user:$SVC allow list,search,add_file,readattr,readextattr,readsecurity" "$HH_LOG_DIR" 2>/dev/null || true
for f in "$HH_LOG_DIR"/hydrahive2*.log "$HH_LOG_DIR"/agentlink*.log; do
  [ -f "$f" ] || continue
  case "$f" in *-update.log|*-addon.log|*-tailscaled.log) continue ;; esac   # schreiben root-Dienste
  chown "$SVC" "$f"
done

# --- 4) PostgreSQL (eigener Datenordner, Daten aus der alten Datenbank) -------------------------------------------
if [ -n "$PG_DUMP" ]; then
  log "Datenbank umziehen"
  HH_OLD_USER="$OLD" HH_USER="$SVC" HH_PG_DUMP="$PG_DUMP" bash "$LIB/mac-pg-move.sh" || fail "Datenbank-Umzug"
  HH_USER="$SVC" bash "$LIB/mac-postgres-daemon.sh" || fail "Datenbank-Dienst"
fi

# --- 5) Dienst-Dateien neu (UserName/HOME = Konto) ---------------------------------------------------------------
log "Dienste für $SVC neu einrichten"
HH_HOST="${HH_HOST:-127.0.0.1}"
HH_PORT="${HH_PORT:-8001}"
export HH_USER HH_REPO_DIR HH_DATA_DIR HH_CONFIG_DIR HH_HOST HH_PORT
bash "$MODS/50-launchd.sh" || fail "Backend-Dienst"
bash "$MODS/55-launchd-triggers.sh" || fail "Update-Auslöser"
bash "$LIB/mac-addon-trigger.sh" || fail "Zusatz-Module-Auslöser"
if [ -s "$HH_CONFIG_DIR/pg_mirror.dsn" ] && [ -f "$MODS/75-agentlink.sh" ]; then
  bash "$MODS/75-agentlink.sh" || fail "AgentLink"
fi
grep -q '^HH_INSTALL_CONTAINERS=yes' "$CONF" && { bash "$MODS/70-containers.sh" || fail "Container"; }
grep -q '^HH_INSTALL_VOICE=yes' "$CONF" && { bash "$MODS/55-voice.sh" || fail "Voice"; }
[ -x "$TS_BIN/tailscale" ] && { "$TS_BIN/tailscale" set --operator="$SVC" || true; }

# --- 6) Prüfen, dann Merker -------------------------------------------------------------------------------------
ok=""
for ((i = 0; i < WAIT; i++)); do
  if curl -fs -m 3 "http://127.0.0.1:${HH_PORT:-8001}/api/health" >/dev/null; then ok=1; break; fi
  sleep 2
done
[ -n "$ok" ] || fail "Backend antwortet nicht"
hh_conf_set "$CONF" HH_SERVICE_USER "$SVC"
log "Umzug fertig: HydraHive läuft jetzt als $SVC (Sicherung: $BACKUP)"
