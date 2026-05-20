#!/usr/bin/env bash
# SearXNG — privater Meta-Suchmaschinen-Service für HydraHive-Agents.
#
# Idempotent: prüft jeden Schritt einzeln.
# Läuft als systemd-Service auf Port 8888 (konfigurierbar via HH_SEARXNG_PORT).
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

if [ "${HH_INSTALL_SEARXNG:-yes}" = "no" ]; then
  log "SearXNG übersprungen (HH_INSTALL_SEARXNG=no)"
  exit 0
fi

SEARXNG_PORT="${HH_SEARXNG_PORT:-8888}"
SEARXNG_DIR="/opt/searxng"
SEARXNG_USER="searxng"
SEARXNG_VENV="$SEARXNG_DIR/venv"

log "Abhängigkeiten installieren"
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 python3-venv python3-pip git libssl-dev libffi-dev

# System-User anlegen (falls nicht vorhanden)
if ! id "$SEARXNG_USER" &>/dev/null; then
  log "System-User '$SEARXNG_USER' anlegen"
  useradd -r -s /bin/false -d "$SEARXNG_DIR" "$SEARXNG_USER"
fi

# SearXNG clonen / updaten
if [ ! -d "$SEARXNG_DIR/.git" ]; then
  log "SearXNG clonen"
  git clone https://github.com/searxng/searxng "$SEARXNG_DIR" --depth=1 2>&1 | tail -3
else
  log "SearXNG bereits vorhanden — überspringe Clone"
fi

# Virtualenv + Abhängigkeiten
if [ ! -f "$SEARXNG_VENV/bin/python" ]; then
  log "Virtualenv erstellen"
  python3 -m venv "$SEARXNG_VENV"
fi

log "Python-Abhängigkeiten installieren"
"$SEARXNG_VENV/bin/pip" install -q --upgrade pip
"$SEARXNG_VENV/bin/pip" install -q -e "$SEARXNG_DIR"

# Konfiguration erstellen (falls nicht vorhanden)
SEARXNG_SETTINGS="$SEARXNG_DIR/searx/settings.yml"
if [ ! -f "$SEARXNG_SETTINGS" ]; then
  log "Standard-Konfiguration übernehmen"
  cp "$SEARXNG_DIR/searx/settings.yml.example" "$SEARXNG_SETTINGS" 2>/dev/null || \
  cp "$SEARXNG_DIR/searx/settings_loader.py" "$SEARXNG_SETTINGS" 2>/dev/null || true
fi

# Secret-Key setzen (einmalig generieren)
if [ -f "$SEARXNG_SETTINGS" ]; then
  if grep -q "ultrasecretkey\|change_this" "$SEARXNG_SETTINGS" 2>/dev/null; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    log "Secret-Key generieren"
    sed -i "s|ultrasecretkey|$SECRET|g; s|change_this.*|$SECRET|g" "$SEARXNG_SETTINGS"
  fi
  # Bind-Adresse auf 0.0.0.0 setzen damit HydraHive erreichbar ist
  sed -i "s|bind_address:.*|bind_address: \"0.0.0.0\"|g" "$SEARXNG_SETTINGS" || true
  sed -i "s|port:.*|port: $SEARXNG_PORT|g" "$SEARXNG_SETTINGS" || true
fi

# Berechtigungen setzen
chown -R "$SEARXNG_USER:$SEARXNG_USER" "$SEARXNG_DIR"

# systemd-Service
cat > /etc/systemd/system/searxng.service <<EOF
[Unit]
Description=SearXNG Metasearch Engine
After=network.target

[Service]
Type=simple
User=$SEARXNG_USER
WorkingDirectory=$SEARXNG_DIR
ExecStart=$SEARXNG_VENV/bin/python -m searx.webapp
Environment=SEARXNG_SETTINGS_PATH=$SEARXNG_SETTINGS
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable searxng
systemctl restart searxng

log "SearXNG gestartet auf http://localhost:$SEARXNG_PORT"
log "Für ProjektX: PROJEKTX_SEARXNG_URL=http://localhost:$SEARXNG_PORT"
log "Für HydraHive-Agents: WEB_SEARCH_URL=http://localhost:$SEARXNG_PORT"
