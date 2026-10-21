#!/bin/bash
# macOS: HydraLink (AgentLink) – Gegenstück zu installer/modules/75-agentlink.sh (Linux).
#
# Klont github.com/hydrahive/hydralink nach /opt/hydralink (oder aktualisiert es) und ruft dessen
# installer/install-mac.sh: AgentLink-Backend (9000) + Dashboard (9001) als LaunchDaemons, Datenbank im
# postgresql@16 des Kerns, Nachrichtenkanal im Speicher (kein Redis auf dem Mac).
#
# Läuft aus install-mac.sh (als Nutzer, sudo bei Bedarf) und aus update-mac.sh (als root, LaunchDaemon).
# Der Kern findet AgentLink ohne weitere Einstellung unter http://127.0.0.1:9000 (settings/_services.py).
# Plan: docs/plans/mac-agentlink.md. Abschalten: HH_INSTALL_AGENTLINK=no.
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

if [ "${HH_INSTALL_AGENTLINK:-yes}" = "no" ]; then
  log "AgentLink übersprungen (HH_INSTALL_AGENTLINK=no)"
  exit 0
fi

HH_USER="${HH_USER:?HH_USER fehlt}"
HL_DIR="${HL_DIR:-/opt/hydralink}"
HL_REPO_URL="${HL_REPO_URL:-https://github.com/hydrahive/hydralink.git}"
export HL_BACKEND_PORT="${HL_BACKEND_PORT:-9000}"
export HL_FRONTEND_PORT="${HL_FRONTEND_PORT:-9001}"

as_root() { [ "$(id -u)" -eq 0 ]; }
# git als Dienstnutzer: als root lehnt git das fremde Repo ab („dubious ownership“).
as_user() { if as_root; then sudo -u "$HH_USER" "$@"; else "$@"; fi; }
priv() { if as_root; then "$@"; else sudo "$@"; fi; }

if [ ! -d "$HL_DIR/.git" ]; then
  log "Klone hydralink nach $HL_DIR"
  priv mkdir -p "$HL_DIR"
  priv chown "$HH_USER" "$HL_DIR"
  as_user git clone --quiet "$HL_REPO_URL" "$HL_DIR"
else
  log "Aktualisiere hydralink in $HL_DIR"
  priv chown -R "$HH_USER" "$HL_DIR"
  as_user git -C "$HL_DIR" pull --ff-only --quiet
fi

# install-mac.sh: als Nutzer direkt; als root mit HL_USER (es ruft brew/pip/npm dann als HL_USER).
HL_USER="$HH_USER" HL_PREFIX="$HL_DIR" bash "$HL_DIR/installer/install-mac.sh"
