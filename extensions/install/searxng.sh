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
    python3 python3-venv python3-dev python3-pip git curl \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true

# venv über den gemeinsamen Helfer: System-Python >= 3.12, aufgelöst auf die
# versionierte Datei, Neubau bei abweichender Version (Spec python-314-umstieg).
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../installer/lib" && pwd)"
# shellcheck source=installer/lib/python-venv.sh
source "${LIB_DIR}/python-venv.sh"
# shellcheck source=installer/lib/searxng-venv.sh
source "${LIB_DIR}/searxng-venv.sh"

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
    hh_searxng_sync_venv "${SEARXNG_DIR}" "${SEARXNG_USER}" "" || die "SearXNG-venv konnte nicht erneuert werden"
    sudo -u "${SEARXNG_USER}" "${SEARXNG_DIR}/venv/bin/pip" install -qU searxng 2>/dev/null || true

    # JSON-Format nachrüsten (idempotent) — heilt ältere Installationen ohne
    # format=json, damit web_search/API funktioniert. Kein /opt von Hand nötig.
    SETTINGS="${SEARXNG_DIR}/searxng/settings.yml"
    if [ -f "${SETTINGS}" ] && ! grep -qE '^[[:space:]]*-[[:space:]]*json[[:space:]]*$' "${SETTINGS}"; then
        if grep -qE '^[[:space:]]*formats[[:space:]]*:' "${SETTINGS}"; then
            warn "settings.yml hat einen formats-Block ohne json — bitte '- json' manuell ergänzen"
        else
            info "Aktiviere JSON-Format in settings.yml..."
            python3 - "${SETTINGS}" <<'PYEOF'
import sys
p = sys.argv[1]
lines = open(p, encoding="utf-8").read().splitlines()
out = []
for line in lines:
    out.append(line)
    if line.rstrip() == "search:":
        out += ["  formats:", "    - html", "    - json"]
open(p, "w", encoding="utf-8").write("\n".join(out) + "\n")
PYEOF
            chown "${SEARXNG_USER}:${SEARXNG_USER}" "${SETTINGS}" 2>/dev/null || true
        fi
    fi

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
# Legt das venv an und installiert requirements.txt (statt editable install —
# pip install -e schlägt fehl, solange Build-Deps wie msgspec fehlen).
hh_searxng_sync_venv "${SEARXNG_DIR}" "${SEARXNG_USER}" "" || die "pip install fehlgeschlagen"
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
  # JSON-Format aktiv: HydraHives web_search-Tool (und jede API-Nutzung) braucht
  # format=json. SearXNG liefert sonst nur HTML → 403 auf JSON-Anfragen.
  formats:
    - html
    - json
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
