#!/usr/bin/env bash
set -euo pipefail

log()  { printf "\033[1;36m[tailscale-install]\033[0m %s\n" "$*"; }
err()  { printf "\033[1;31m[tailscale-install]\033[0m %s\n" "$*" >&2; exit 1; }

HH_USER="${HH_USER:-hydrahive}"
HH_TAILSCALE_AUTHKEY="${HH_TAILSCALE_AUTHKEY:-}"

log "Tailscale installieren"
if ! command -v tailscale &>/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
else
  log "Tailscale bereits installiert ($(tailscale version 2>/dev/null | head -1))"
fi

log "tailscaled aktivieren"
systemctl enable tailscaled
systemctl start tailscaled || true

# Operator setzen statt sudoers — hydrahive kann tailscale up/logout/status
# dann direkt via /run/tailscale/tailscaled.sock aufrufen, ohne sudo.
# Funktioniert auch wenn der Service mit NoNewPrivileges=true läuft.
log "Tailscale-Operator auf ${HH_USER} setzen"
tailscale set --operator="${HH_USER}" 2>/dev/null \
  || log "tailscale set --operator fehlgeschlagen (alte tailscale-Version?) — bitte manuell prüfen"

# Alte sudoers-Regel aufräumen falls sie aus früheren Installs vorhanden ist
[ -f /etc/sudoers.d/hydrahive-tailscale ] && rm -f /etc/sudoers.d/hydrahive-tailscale

if [ -n "$HH_TAILSCALE_AUTHKEY" ]; then
  # --accept-routes default OFF: sonst werden Tailnet-Subnet/Exit-Routes
  # auf den Host gepusht und das LAN-Default-Interface verschwindet aus
  # `ip route get`. Opt-in via HH_TAILSCALE_ACCEPT_ROUTES=yes.
  TS_FLAGS="--operator=${HH_USER}"
  if [ "${HH_TAILSCALE_ACCEPT_ROUTES:-no}" = "yes" ]; then
    TS_FLAGS="$TS_FLAGS --accept-routes"
  fi
  log "Tailscale verbinden mit Auth-Key (Flags: $TS_FLAGS)"
  tailscale up --authkey="$HH_TAILSCALE_AUTHKEY" $TS_FLAGS \
    || log "tailscale up fehlgeschlagen — manuell verbinden"
fi

log "Fertig. Tailscale $(tailscale status --json 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"BackendState\",\"?\"))' 2>/dev/null || echo '?')"
