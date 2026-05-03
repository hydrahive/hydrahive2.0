#!/usr/bin/env bash
# HydraHive2 — Installer für Ubuntu / Debian.
#
# Voraussetzungen: läuft als root (sudo). Frische VM oder bestehender Server,
# Repo wurde nach /opt/hydrahive2 geklont (oder dieser Pfad existiert).
#
# Usage:
#   sudo ./install.sh                    # interaktiv mit Defaults
#   sudo HH_HOST=192.168.1.10 ./install.sh
#
# Was passiert:
#   1. apt-Dependencies (python3.12, node, nginx)
#   2. System-User 'hydrahive' anlegen
#   3. Verzeichnisse /var/lib/hydrahive2 + /etc/hydrahive2
#   4. Python-venv im Repo, hydrahive-core via pip install -e
#   5. Frontend bauen (npm install + run build)
#   6. WhatsApp-Bridge: npm-Module installieren
#   7. systemd-Service installieren + starten
#   8. (optional) nginx-Reverse-Proxy
set -euo pipefail

# --------------------------------------------------------------- Konfiguration
HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_USER="${HH_USER:-hydrahive}"
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/etc/hydrahive2}"
HH_HOST="${HH_HOST:-127.0.0.1}"
HH_PORT="${HH_PORT:-8001}"
HH_INSTALL_NGINX="${HH_INSTALL_NGINX:-yes}"

# --------------------------------------------------------------- Helfer
log() { printf "\033[1;36m[hh2-install]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-install]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Bitte mit sudo / als root ausführen."
[ -d "$HH_REPO_DIR" ] || err "Repo-Verzeichnis $HH_REPO_DIR existiert nicht."

INSTALLER_DIR="$(cd "$(dirname "$0")" && pwd)"

export HH_REPO_DIR HH_USER HH_DATA_DIR HH_CONFIG_DIR HH_HOST HH_PORT INSTALLER_DIR

# --------------------------------------------------------------- Module
log "Phase 1: System-Dependencies"
bash "$INSTALLER_DIR/modules/00-deps.sh"

log "Phase 2: System-User"
bash "$INSTALLER_DIR/modules/10-user.sh"

log "Phase 3: Verzeichnisse + Permissions"
bash "$INSTALLER_DIR/modules/20-paths.sh"

log "Phase 4: Python-venv + Backend"
bash "$INSTALLER_DIR/modules/30-python.sh"

log "Phase 5: Frontend"
bash "$INSTALLER_DIR/modules/40-frontend.sh"

log "Phase 6: WhatsApp-Bridge"
bash "$INSTALLER_DIR/modules/45-whatsapp.sh"

log "Phase 7a: Samba (Projekt-Workspace-Shares)"
bash "$INSTALLER_DIR/modules/47-samba.sh"

log "Phase 7b: PostgreSQL Datamining-Mirror"
if [ "${HH_INSTALL_POSTGRES:-yes}" != "no" ]; then
  bash "$INSTALLER_DIR/modules/48-postgres.sh"
else
  log "PostgreSQL übersprungen (HH_INSTALL_POSTGRES=no)"
fi

log "Phase 7: systemd-Service"
bash "$INSTALLER_DIR/modules/50-systemd.sh"

if [ "${HH_INSTALL_NGINX}" != "no" ]; then
  log "Phase 8: nginx"
  bash "$INSTALLER_DIR/modules/60-nginx.sh"
else
  log "Phase 8: nginx übersprungen (HH_INSTALL_NGINX=no)"
fi

log "Phase 9: VM-Manager (QEMU/KVM + websockify)"
bash "$INSTALLER_DIR/modules/65-vms.sh"

log "Phase 10: Container-Manager (incus + dir-Storage)"
bash "$INSTALLER_DIR/modules/70-containers.sh"

log "Phase 11: HydraLink (AgentLink)"
bash "$INSTALLER_DIR/modules/75-agentlink.sh"

log "Phase 12: Tailscale"
if [ "${HH_INSTALL_TAILSCALE:-yes}" != "no" ]; then
  bash "$INSTALLER_DIR/modules/80-tailscale.sh"
else
  log "Tailscale übersprungen (HH_INSTALL_TAILSCALE=no)"
fi

# ----------------------------------------------------------------- Zusammenfassung
SERVER_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '/src/{print $7; exit}' || hostname -I 2>/dev/null | awk '{print $1}')
SERVER_URL="https://${SERVER_IP:-<server-ip>}"

# Admin-Passwort aus Journal lesen — Service läuft bereits seit Phase 7
ADMIN_PW=""
for _ in 1 2 3 4 5; do
  ADMIN_PW=$(journalctl -u hydrahive2 --no-pager -n 100 2>/dev/null \
    | grep "Passwort:" | tail -1 | awk '{print $NF}')
  [ -n "$ADMIN_PW" ] && break
  sleep 2
done

printf "\n"
printf "\033[1;32m╔══════════════════════════════════════════════╗\033[0m\n"
printf "\033[1;32m║        HydraHive2 — Installation fertig      ║\033[0m\n"
printf "\033[1;32m╠══════════════════════════════════════════════╣\033[0m\n"
printf "\033[1;32m║\033[0m  URL:       \033[1;37m%-33s\033[0m\033[1;32m║\033[0m\n" "$SERVER_URL"
printf "\033[1;32m║\033[0m  Benutzer:  \033[1;37m%-33s\033[0m\033[1;32m║\033[0m\n" "admin"
if [ -n "$ADMIN_PW" ]; then
  printf "\033[1;32m║\033[0m  Passwort:  \033[1;33m%-33s\033[0m\033[1;32m║\033[0m\n" "$ADMIN_PW"
else
  printf "\033[1;32m║\033[0m  Passwort:  \033[1;33m%-33s\033[0m\033[1;32m║\033[0m\n" "(siehe: journalctl -u hydrahive2)"
fi
printf "\033[1;32m╠══════════════════════════════════════════════╣\033[0m\n"
printf "\033[1;32m║\033[0m  Browser: Zertifikatswarnung mit 'Weiter'     \033[1;32m║\033[0m\n"
printf "\033[1;32m║\033[0m  Passwort nach erstem Login ändern!           \033[1;32m║\033[0m\n"
printf "\033[1;32m╚══════════════════════════════════════════════╝\033[0m\n"
printf "\n"
