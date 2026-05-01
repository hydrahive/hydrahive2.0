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

log "sudoers-Regel für ${HH_USER} einrichten"
cat > /etc/sudoers.d/hydrahive-tailscale << EOF
${HH_USER} ALL=(ALL) NOPASSWD: /usr/bin/tailscale status *
${HH_USER} ALL=(ALL) NOPASSWD: /usr/bin/tailscale up *
${HH_USER} ALL=(ALL) NOPASSWD: /usr/bin/tailscale logout
EOF
chmod 440 /etc/sudoers.d/hydrahive-tailscale
visudo -c -f /etc/sudoers.d/hydrahive-tailscale || err "sudoers-Syntax ungültig"

if [ -n "$HH_TAILSCALE_AUTHKEY" ]; then
  log "Tailscale verbinden mit Auth-Key"
  tailscale up --authkey="$HH_TAILSCALE_AUTHKEY" --accept-routes || log "tailscale up fehlgeschlagen — manuell verbinden"
fi

log "Fertig. Tailscale $(tailscale status --json 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get(\"BackendState\",\"?\"))' 2>/dev/null || echo '?')"
