#!/usr/bin/env bash
# HydraHive2 — nachträglicher LLM-Provider-Wizard (analog zu `openclaw onboard`).
#
# Ruft den interaktiven Wizard aus installer/lib/llm-wizard.sh auf, damit
# Provider-Keys auch ohne komplette Re-Installation eingetragen werden können.
#
# Usage:
#   sudo bash /opt/hydrahive2/installer/onboard.sh                  # nur fragen wenn noch leer
#   sudo bash /opt/hydrahive2/installer/onboard.sh --reconfigure    # erneut, auch wenn schon Werte da
set -euo pipefail

HH_CONFIG_DIR="${HH_CONFIG_DIR:-/etc/hydrahive2}"
HH_USER="${HH_USER:-hydrahive}"
INSTALLER_DIR="$(cd "$(dirname "$0")" && pwd)"

log() { printf "\033[1;36m[hh2-onboard]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-onboard]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Bitte mit sudo / als root ausführen."

RECONFIGURE=0
NO_PROMPT=0
for arg in "$@"; do
  case "$arg" in
    --reconfigure) RECONFIGURE=1 ;;
    --no-prompt)   NO_PROMPT=1   ;;
  esac
done

is_tty() { [ -t 0 ] && [ -t 1 ] && [ -r /dev/tty ]; }

# shellcheck source=lib/llm-wizard.sh
source "$INSTALLER_DIR/lib/llm-wizard.sh"

llm_wizard

# Service neu starten damit der mtime-Cache greift
if [ -f "$HH_CONFIG_DIR/llm.json" ]; then
  log "Service neu starten (Config-Cache invalidieren)"
  systemctl restart hydrahive2.service 2>/dev/null || true
fi

log "Fertig — Web-UI auf https://<server>/ öffnen, du kannst direkt chatten."
