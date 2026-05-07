#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }

GITEA_VERSION="1.21.11"
GITEA_BINARY="/usr/local/bin/gitea"
GITEA_WORK_DIR="/opt/gitea"
GITEA_CONF_DIR="/etc/gitea"
GITEA_CONF="${GITEA_CONF_DIR}/app.ini"
GITEA_SERVICE="gitea"
GITEA_USER="git"
GITEA_PORT="3000"
GITEA_ADMIN="hydrahive"
GITEA_CONFIG_FILE="/etc/hydrahive2/gitea_config.json"
NGINX_CONF="/etc/nginx/sites-available/gitea"

_gitea_admin() {
    sudo -u "${GITEA_USER}" env HOME="${GITEA_WORK_DIR}" GITEA_WORK_DIR="${GITEA_WORK_DIR}" "${GITEA_BINARY}" "$@"
}

info "Installiere Gitea ${GITEA_VERSION}..."

# ── Binary ──────────────────────────────────────────────────────────────────
if [ -f "${GITEA_BINARY}" ] && "${GITEA_BINARY}" --version 2>/dev/null | grep -q "${GITEA_VERSION}"; then
    info "Gitea ${GITEA_VERSION} bereits installiert — überspringe Download"
else
    GITEA_URL="https://dl.gitea.com/gitea/${GITEA_VERSION}/gitea-${GITEA_VERSION}-linux-amd64"
    info "Lade Gitea ${GITEA_VERSION}..."
    curl -fsSL -o "${GITEA_BINARY}.tmp" "${GITEA_URL}"
    mv "${GITEA_BINARY}.tmp" "${GITEA_BINARY}"
    chmod +x "${GITEA_BINARY}"
    success "Gitea-Binary installiert"
fi

# ── System-User + Verzeichnisse ─────────────────────────────────────────────
if ! id "${GITEA_USER}" &>/dev/null; then
    useradd --system --shell /bin/bash --home-dir "${GITEA_WORK_DIR}" --create-home "${GITEA_USER}"
    success "System-User '${GITEA_USER}' angelegt"
fi
mkdir -p "${GITEA_WORK_DIR}/data" "${GITEA_WORK_DIR}/log" "${GITEA_WORK_DIR}/custom"
chown -R "${GITEA_USER}:${GITEA_USER}" "${GITEA_WORK_DIR}"
mkdir -p "${GITEA_CONF_DIR}"
chown root:"${GITEA_USER}" "${GITEA_CONF_DIR}"
chmod 750 "${GITEA_CONF_DIR}"

# ── app.ini (idempotent) ─────────────────────────────────────────────────────
if [ ! -f "${GITEA_CONF}" ]; then
    info "Schreibe Gitea-Konfiguration..."
    SK=$(openssl rand -hex 32)
    IT=$(openssl rand -hex 32)
    _raw="$(openssl rand -base64 64)"; _clean="${_raw//[\/+=]/}"; JWT="${_clean:0:43}"
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

    cat > "${GITEA_CONF}" << APPINI
APP_NAME = HydraHive Gitea
RUN_USER = ${GITEA_USER}
RUN_MODE = prod

[database]
DB_TYPE  = sqlite3
PATH     = ${GITEA_WORK_DIR}/data/gitea.db

[repository]
ROOT = ${GITEA_WORK_DIR}/data/repositories

[server]
HTTP_ADDR    = 127.0.0.1
HTTP_PORT    = ${GITEA_PORT}
ROOT_URL     = http://${SERVER_IP}:${GITEA_PORT}/
DOMAIN       = ${SERVER_IP}
DISABLE_SSH  = true
OFFLINE_MODE = true

[security]
INSTALL_LOCK   = true
SECRET_KEY     = ${SK}
INTERNAL_TOKEN = ${IT}

[oauth2]
JWT_SECRET = ${JWT}

[service]
DISABLE_REGISTRATION       = true
REQUIRE_SIGNIN_VIEW        = false
DEFAULT_KEEP_EMAIL_PRIVATE = true

[log]
ROOT_PATH = ${GITEA_WORK_DIR}/log
MODE      = file
LEVEL     = Warn
APPINI

    chown root:"${GITEA_USER}" "${GITEA_CONF}"
    chmod 660 "${GITEA_CONF}"
    success "Gitea app.ini geschrieben"
else
    info "Gitea app.ini bereits vorhanden — überspringe"
fi

# ── systemd-Service ──────────────────────────────────────────────────────────
cat > "/etc/systemd/system/${GITEA_SERVICE}.service" << UNIT
[Unit]
Description=Gitea (HydraHive Git-Server)
After=network.target

[Service]
Type=simple
User=${GITEA_USER}
Group=${GITEA_USER}
WorkingDirectory=${GITEA_WORK_DIR}
ExecStart=${GITEA_BINARY} web --config ${GITEA_CONF} --work-path ${GITEA_WORK_DIR}
Restart=always
RestartSec=5
Environment=HOME=${GITEA_WORK_DIR}

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable "${GITEA_SERVICE}" &>/dev/null
if systemctl is-active --quiet "${GITEA_SERVICE}"; then
    systemctl restart "${GITEA_SERVICE}"
else
    systemctl start "${GITEA_SERVICE}"
fi
success "Gitea-Service gestartet"

# ── Warten ───────────────────────────────────────────────────────────────────
GITEA_OK=0
for i in $(seq 1 20); do
    sleep 3
    if curl -sf --max-time 5 "http://127.0.0.1:${GITEA_PORT}/api/v1/version" &>/dev/null; then
        GITEA_OK=1
        break
    fi
    info "Warte auf Gitea... (${i}/20)"
done

if [ "${GITEA_OK}" -eq 0 ]; then
    warn "Gitea antwortet nicht — prüfe: journalctl -u ${GITEA_SERVICE} -n 20"
    exit 1
fi
success "Gitea läuft auf http://127.0.0.1:${GITEA_PORT}"

# ── Admin-User + Token ───────────────────────────────────────────────────────
sleep 3
GITEA_ADMIN_PASS="${GITEA_ADMIN_PASS:-$(openssl rand -base64 16 | tr -d '/+=' | head -c 20)}"

EXISTING=$(curl -sf "http://127.0.0.1:${GITEA_PORT}/api/v1/users/search?q=${GITEA_ADMIN}" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('ok' if d.get('data') else 'missing')" 2>/dev/null || echo "missing")

if [ "${EXISTING}" = "missing" ]; then
    _gitea_admin admin user create \
        --config "${GITEA_CONF}" --work-path "${GITEA_WORK_DIR}" \
        --username "${GITEA_ADMIN}" --password "${GITEA_ADMIN_PASS}" \
        --email "admin@hydrahive.local" --admin --must-change-password=false
    success "Admin-User '${GITEA_ADMIN}' angelegt"
else
    _gitea_admin admin user change-password \
        --config "${GITEA_CONF}" --work-path "${GITEA_WORK_DIR}" \
        --username "${GITEA_ADMIN}" --password "${GITEA_ADMIN_PASS}"
    info "Admin-User '${GITEA_ADMIN}' Passwort aktualisiert"
fi

GITEA_TOKEN=$(_gitea_admin admin user generate-access-token \
    --config "${GITEA_CONF}" --work-path "${GITEA_WORK_DIR}" \
    --username "${GITEA_ADMIN}" \
    --token-name "hydrahive2-$(date +%s)" \
    --scopes "write:repository,read:repository,write:user,read:user,write:issue,read:issue" \
    --raw 2>/dev/null | tr -d '[:space:]') || GITEA_TOKEN=""

mkdir -p /etc/hydrahive2 /etc/hydrahive2/extensions
cat > "${GITEA_CONFIG_FILE}" << GITCFG
{
  "url": "http://127.0.0.1:${GITEA_PORT}",
  "token": "${GITEA_TOKEN}",
  "admin_user": "${GITEA_ADMIN}",
  "admin_pass": "${GITEA_ADMIN_PASS}"
}
GITCFG
chmod 600 "${GITEA_CONFIG_FILE}"
success "Gitea-Config: ${GITEA_CONFIG_FILE}"

# Standardisierte Credentials für den Credentials-Tab
cat > "/etc/hydrahive2/extensions/gitea.credentials.json" << CREDFILE
{
  "id": "gitea",
  "name": "Git-Server (Gitea)",
  "fields": [
    {"label": "URL", "value": "http://127.0.0.1:${GITEA_PORT}", "secret": false},
    {"label": "Admin-User", "value": "${GITEA_ADMIN}", "secret": false},
    {"label": "Admin-Passwort", "value": "${GITEA_ADMIN_PASS}", "secret": true},
    {"label": "API-Token", "value": "${GITEA_TOKEN}", "secret": true}
  ]
}
CREDFILE
chown root:hydrahive /etc/hydrahive2/extensions/gitea.credentials.json
chmod 640 /etc/hydrahive2/extensions/gitea.credentials.json

# ── nginx-Proxy ──────────────────────────────────────────────────────────────
if command -v nginx &>/dev/null; then
    cat > "${NGINX_CONF}" << NGINXCONF
server {
    listen 3001;
    server_name _;
    client_max_body_size 50M;
    location / {
        proxy_pass         http://127.0.0.1:${GITEA_PORT};
        proxy_set_header   Host             \$host;
        proxy_set_header   X-Real-IP        \$remote_addr;
        proxy_set_header   X-Forwarded-For  \$proxy_add_x_forwarded_for;
    }
}
NGINXCONF
    ln -sf "${NGINX_CONF}" /etc/nginx/sites-enabled/gitea
    nginx -t && systemctl reload nginx && success "nginx: Gitea-Proxy auf Port 3001"
fi

success "Gitea vollständig installiert"
info "  URL:    http://127.0.0.1:${GITEA_PORT}"
info "  Login:  ${GITEA_ADMIN} / ${GITEA_ADMIN_PASS}"
