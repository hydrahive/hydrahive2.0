#!/usr/bin/env bash
# Phase 11: HydraLink — AgentLink-Service (siehe github.com/hydrahive/hydralink)
#
# Klont das hydralink-Repo nach /opt/hydralink wenn nicht vorhanden, und
# ruft seinen Installer (apt → Postgres + Redis, Python venv → AgentLink-
# Backend, npm build → AgentLink-Frontend, systemd-Units für beide).
#
# Idempotent: bei zweitem Aufruf wird gepullt + neu installiert (Updates).
# Wenn HH_SKIP_AGENTLINK=yes gesetzt ist, wird übersprungen.
set -euo pipefail

if [ "${HH_SKIP_AGENTLINK:-no}" = "yes" ] || [ "${HH_INSTALL_AGENTLINK:-yes}" = "no" ]; then
  echo "AgentLink übersprungen (HH_INSTALL_AGENTLINK=no)"
  exit 0
fi

HL_DIR="${HL_DIR:-/opt/hydralink}"
HL_REPO_URL="${HL_REPO_URL:-https://github.com/hydrahive/hydralink.git}"
# Ports — passend zu hydralink-Default. 8000 ist oft belegt → 9000 als Default.
export HL_BACKEND_PORT="${HL_BACKEND_PORT:-9000}"
export HL_FRONTEND_PORT="${HL_FRONTEND_PORT:-9001}"
export HL_BIND_HOST="${HL_BIND_HOST:-127.0.0.1}"

if [ ! -d "$HL_DIR/.git" ]; then
  echo "Klone hydralink nach $HL_DIR"
  git clone "$HL_REPO_URL" "$HL_DIR"
else
  echo "Update hydralink in $HL_DIR"
  git -C "$HL_DIR" -c safe.directory="$HL_DIR" pull --ff-only
fi

# Hydralink installieren — bringt Postgres, Redis, AgentLink-Backend, Frontend
bash "$HL_DIR/installer/install.sh"

# HydraHive2-Service ENV erweitern damit ask_agent den lokalen AgentLink kennt.
# Wir patchen die Service-Unit über ein Drop-in damit /etc/systemd/system/
# hydrahive2.service.d/agentlink.conf modular bleibt.
mkdir -p /etc/systemd/system/hydrahive2.service.d
cat > /etc/systemd/system/hydrahive2.service.d/agentlink.conf <<EOF
[Service]
Environment=HH_AGENTLINK_URL=http://${HL_BIND_HOST}:${HL_BACKEND_PORT}
Environment=HH_AGENTLINK_DASHBOARD_URL=/agentlink/
Environment=HH_AGENTLINK_AGENT_ID=hydrahive
EOF

systemctl daemon-reload
systemctl restart hydrahive2.service

echo "HydraHive2 verbindet sich jetzt mit AgentLink auf ${HL_BIND_HOST}:${HL_BACKEND_PORT}"
