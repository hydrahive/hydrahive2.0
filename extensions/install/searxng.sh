#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

SEARXNG_DIR="/opt/searxng"
SEARXNG_USER="searxng"
SEARXNG_PORT="8888"
SECRET_KEY="$(head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 48)"

info "Installiere SearXNG..."

# --- Abhängigkeiten ---
apt-get update -qq
apt-get install -y --quiet \
    python3 python3-venv python3-pip git curl \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true

# --- System-User ---
if ! id "${SEARXNG_USER}" &>/dev/null; then
    useradd -r -s /bin/false -d "${SEARXNG_DIR}" -m "${SEARXNG_USER}"
    success "System-User '${SEARXNG_USER}' angelegt"
fi

# --- Schon installiert? ---
if [ -d "${SEARXNG_DIR}/.git" ]; then
    info "SearXNG bereits vorhanden — aktualisiere..."
    systemctl stop searxng 2>/dev/null || true
    git -C "${SEARXNG_DIR}" pull --quiet 2>/dev/null || true
    sudo -u "${SEARXNG_USER}" "${SEARXNG_DIR}/venv/bin/pip" install -qU searxng 2>/dev/null || true
    systemctl start searxng
    success "SearXNG aktualisiert"
    exit 0
fi

# --- Klonen ---
info "Klone SearXNG..."
rm -rf "${SEARXNG_DIR}"
git clone --depth 1 https://github.com/searxng/searxng.git "${SEARXNG_DIR}" \
    || die "git clone fehlgeschlagen"
chown -R "${SEARXNG_USER}:${SEARXNG_USER}" "${SEARXNG_DIR}"

# --- Virtualenv + Dependencies ---
info "Erstelle Python-Virtualenv und installiere Abhängigkeiten..."
sudo -u "${SEARXNG_USER}" python3 -m venv "${SEARXNG_DIR}/venv"
sudo -u "${SEARXNG_USER}" "${SEARXNG_DIR}/venv/bin/pip" install -q --upgrade pip setuptools wheel
# requirements.txt statt editable install — pip install -e schlägt fehl wenn
# Build-Deps (msgspec) im venv noch nicht vorhanden sind
sudo -u "${SEARXNG_USER}" "${SEARXNG_DIR}/venv/bin/pip" install -q \
    -r "${SEARXNG_DIR}/requirements.txt" \
    || die "pip install fehlgeschlagen"
success "Python-Abhängigkeiten installiert"

# --- Konfiguration ---
mkdir -p "${SEARXNG_DIR}/searxng"
cat > "${SEARXNG_DIR}/searxng/settings.yml" << CONFEOF
use_default_settings: true

general:
  debug: false
  instance_name: "HydraHive Search"
  privacypolicy_url: false
  donation_url: false
  contact_url: false
  enable_metrics: false

server:
  port: ${SEARXNG_PORT}
  bind_address: "0.0.0.0"
  secret_key: "${SECRET_KEY}"
  limiter: false
  public_instance: false
  image_proxy: true

ui:
  static_use_hash: true
  default_locale: de
  default_theme: simple
  theme_args:
    simple_style: dark

search:
  safe_search: 0
  autocomplete: ""
  default_lang: "de-DE"
CONFEOF
chown -R "${SEARXNG_USER}:${SEARXNG_USER}" "${SEARXNG_DIR}"
success "Konfiguration erstellt"

# --- systemd Service ---
cat > /etc/systemd/system/searxng.service << SVCEOF
[Unit]
Description=SearXNG Metasuchmaschine
After=network.target

[Service]
Type=simple
User=${SEARXNG_USER}
Group=${SEARXNG_USER}
WorkingDirectory=${SEARXNG_DIR}
Environment=SEARXNG_SETTINGS_PATH=${SEARXNG_DIR}/searxng/settings.yml
ExecStart=${SEARXNG_DIR}/venv/bin/python -m searx.webapp
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable --now searxng
success "Service 'searxng' gestartet auf Port ${SEARXNG_PORT}"

# --- Warten ---
info "Warte auf SearXNG (bis 30 s)..."
for i in $(seq 1 15); do
    sleep 2
    curl -sf "http://127.0.0.1:${SEARXNG_PORT}/" &>/dev/null && break || true
done
curl -sf "http://127.0.0.1:${SEARXNG_PORT}/" &>/dev/null \
    && success "SearXNG erreichbar" \
    || warn "SearXNG noch nicht erreichbar — prüfe: journalctl -u searxng"

# --- Credentials ---
SERVER_IP=$(hostname -I | awk '{print $1}')
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/searxng.credentials.json << CREDEOF
{
  "id": "searxng",
  "name": "SearXNG (Metasuchmaschine)",
  "fields": [
    {"label": "URL", "value": "http://${SERVER_IP}:${SEARXNG_PORT}", "secret": false}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/searxng.credentials.json
chmod 640 /etc/hydrahive2/extensions/searxng.credentials.json

success "SearXNG installiert"
info "  URL: http://${SERVER_IP}:${SEARXNG_PORT}"
