#!/usr/bin/env bash
# HydraHive2 — Installer für macOS (Homebrew).
#
# Voraussetzungen:
#   - macOS 13+ mit Homebrew installiert
#   - Repo nach /opt/hydrahive2 geklont (oder HH_REPO_DIR setzen)
#   - Als normaler User ausführen (sudo-Passwort wird abgefragt)
#
# Usage:
#   ./install-mac.sh
#   HH_HOST=0.0.0.0 ./install-mac.sh
set -euo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_USER="${HH_USER:-$(whoami)}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
HH_HOST="${HH_HOST:-127.0.0.1}"
HH_PORT="${HH_PORT:-8001}"
HH_INSTALL_NGINX="${HH_INSTALL_NGINX:-yes}"
HH_INSTALL_POSTGRES="${HH_INSTALL_POSTGRES:-yes}"

log() { printf "\033[1;36m[hh2-mac]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-mac]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(uname)" = "Darwin" ] || err "Nur für macOS."
[ -d "$HH_REPO_DIR" ] || err "Repo nicht gefunden: $HH_REPO_DIR"
command -v brew >/dev/null 2>&1 || err "Homebrew fehlt. Installieren: https://brew.sh"

INSTALLER_DIR="$(cd "$(dirname "$0")" && pwd)"
export HH_REPO_DIR HH_USER HH_DATA_DIR HH_CONFIG_DIR HH_HOST HH_PORT INSTALLER_DIR

log "Phase 1: System-Dependencies"
bash "$INSTALLER_DIR/modules-mac/00-deps.sh"

log "Phase 2: Verzeichnisse"
bash "$INSTALLER_DIR/modules-mac/20-paths.sh"

log "Phase 3: Python-venv + Backend"
bash "$INSTALLER_DIR/modules-mac/30-python.sh"

log "Phase 4: Frontend"
bash "$INSTALLER_DIR/modules-mac/40-frontend.sh"

if [ "${HH_INSTALL_POSTGRES}" != "no" ]; then
  log "Phase 5: PostgreSQL Datamining-Mirror"
  bash "$INSTALLER_DIR/modules-mac/48-postgres.sh"
else
  log "Phase 5: PostgreSQL übersprungen"
fi

log "Phase 6: launchd-Service"
bash "$INSTALLER_DIR/modules-mac/50-launchd.sh"

if [ "${HH_INSTALL_NGINX}" != "no" ]; then
  log "Phase 7: nginx"
  bash "$INSTALLER_DIR/modules-mac/60-nginx.sh"
else
  log "Phase 7: nginx übersprungen"
fi

SERVER_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "<ip>")
SERVER_URL="https://${SERVER_IP}"

ADMIN_PW=""
for _ in 1 2 3 4 5; do
  ADMIN_PW=$(log show --predicate 'process == "uvicorn"' --last 30s 2>/dev/null \
    | grep "Passwort:" | tail -1 | awk '{print $NF}' || true)
  [ -n "$ADMIN_PW" ] && break
  sleep 2
done

printf "\n"
printf "\033[1;32m╔══════════════════════════════════════════════╗\033[0m\n"
printf "\033[1;32m║     HydraHive2 — Installation fertig (Mac)   ║\033[0m\n"
printf "\033[1;32m╠══════════════════════════════════════════════╣\033[0m\n"
printf "\033[1;32m║\033[0m  URL:       \033[1;37m%-33s\033[0m\033[1;32m║\033[0m\n" "$SERVER_URL"
printf "\033[1;32m║\033[0m  Benutzer:  \033[1;37m%-33s\033[0m\033[1;32m║\033[0m\n" "admin"
if [ -n "$ADMIN_PW" ]; then
  printf "\033[1;32m║\033[0m  Passwort:  \033[1;33m%-33s\033[0m\033[1;32m║\033[0m\n" "$ADMIN_PW"
else
  printf "\033[1;32m║\033[0m  Passwort:  \033[1;33m%-33s\033[0m\033[1;32m║\033[0m\n" "(siehe: log show --process uvicorn)"
fi
printf "\033[1;32m╠══════════════════════════════════════════════╣\033[0m\n"
printf "\033[1;32m║\033[0m  Service:   launchctl list io.hydrahive.backend\033[1;32m ║\033[0m\n"
printf "\033[1;32m╚══════════════════════════════════════════════╝\033[0m\n"
printf "\n"
