#!/usr/bin/env bash
# Dev-Start für HydraHive2 — Backend + Frontend
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Dev-Datenpfade — im User-Home, überlebt Reboot.
# Production-Default ist /var/lib/hydrahive2 + /etc/hydrahive2 (sudo nötig).
export HH_BASE_DIR="${HH_BASE_DIR:-$SCRIPT_DIR}"
export HH_DATA_DIR="${HH_DATA_DIR:-$HOME/.hh2-dev/data}"
export HH_CONFIG_DIR="${HH_CONFIG_DIR:-$HOME/.hh2-dev/config}"
export HH_SECRET_KEY="${HH_SECRET_KEY:-devsecret123}"
export HH_ENABLE_DOCS="${HH_ENABLE_DOCS:-1}"
export HH_PORT="${HH_PORT:-8001}"
export HH_INTERNAL_URL="${HH_INTERNAL_URL:-http://127.0.0.1:8001}"
# AgentLink (siehe github.com/hydrahive/hydralink) — wenn lokal installiert
# auf 9000, automatisch verbinden. Sonst auskommentieren.
export HH_AGENTLINK_URL="${HH_AGENTLINK_URL:-http://127.0.0.1:9000}"
export HH_AGENTLINK_AGENT_ID="${HH_AGENTLINK_AGENT_ID:-hydrahive-dev}"
export HH_AGENTLINK_DASHBOARD_URL="${HH_AGENTLINK_DASHBOARD_URL:-http://127.0.0.1:9001}"

mkdir -p "$HH_DATA_DIR" "$HH_CONFIG_DIR"

# Admin anlegen falls noch nicht vorhanden
if [ ! -f "$HH_CONFIG_DIR/users.json" ]; then
  echo '{"admin":{"password_hash":"240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9","role":"admin"}}' \
    > "$HH_CONFIG_DIR/users.json"
  echo "Admin-User angelegt (admin / admin123)"
fi

echo "==> Backend starten auf http://127.0.0.1:8001"
"$SCRIPT_DIR/.venv/bin/uvicorn" hydrahive.api.main:app \
  --host 127.0.0.1 --port 8001 --reload &
BACKEND_PID=$!

echo "==> Frontend starten"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Restart-Trigger-Watcher: schaut periodisch nach $HH_DATA_DIR/.restart_request
# (geschrieben von der API beim Restart-Knopf) und triggert systemctl --user restart.
(
  while true; do
    if [ -f "$HH_DATA_DIR/.restart_request" ]; then
      rm -f "$HH_DATA_DIR/.restart_request"
      echo "==> Restart-Trigger erkannt — Service wird neu gestartet"
      systemctl --user restart hydrahive2-dev.service 2>&1 || true
      exit 0
    fi
    sleep 1
  done
) &
WATCHER_PID=$!

echo ""
echo "Backend:  http://127.0.0.1:8001"
echo "Frontend: http://localhost:5173 (oder 5174)"
echo ""
echo "Beenden mit Ctrl+C"

trap "kill $BACKEND_PID $FRONTEND_PID $WATCHER_PID 2>/dev/null" EXIT
wait
