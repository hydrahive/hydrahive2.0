#!/usr/bin/env bash
# Dev-Start für HydraHive2 — Backend + Frontend
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Dev-Datenpfade — im User-Home, überlebt Reboot.
# Production-Default ist /var/lib/hydrahive2 + /etc/hydrahive2 (sudo nötig).
export HH_DATA_DIR="${HH_DATA_DIR:-$HOME/.hh2-dev/data}"
export HH_CONFIG_DIR="${HH_CONFIG_DIR:-$HOME/.hh2-dev/config}"
export HH_SECRET_KEY="${HH_SECRET_KEY:-devsecret123}"
export HH_ENABLE_DOCS="${HH_ENABLE_DOCS:-1}"

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

echo ""
echo "Backend:  http://127.0.0.1:8001"
echo "Frontend: http://localhost:5173 (oder 5174)"
echo ""
echo "Beenden mit Ctrl+C"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
