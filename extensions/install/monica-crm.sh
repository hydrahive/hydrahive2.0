#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

MONICA_DIR="/opt/monica"
MONICA_USER="monica"
MONICA_DB="monica"
MONICA_DB_USER="monica"
MONICA_DB_PASS="$(head -c 16 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 24)"
MONICA_PORT="8180"

info "Installiere Monica CRM..."

# --- Schon installiert? ---
if [ -d "${MONICA_DIR}" ] && [ -f "${MONICA_DIR}/.env" ]; then
    info "Monica bereits installiert — aktualisiere..."
    cd "${MONICA_DIR}"
    sudo -u "${MONICA_USER}" git pull --quiet 2>/dev/null || true
    sudo -u "${MONICA_USER}" composer install --no-dev --no-interaction --quiet 2>/dev/null || true
    sudo -u "${MONICA_USER}" php artisan migrate --force --quiet 2>/dev/null || true
    success "Monica aktualisiert"
    exit 0
fi

# --- Abhängigkeiten ---
info "Installiere Abhängigkeiten (PHP 8.3, MySQL, Composer)..."
apt-get update -qq
apt-get install -y --quiet \
    php8.3-fpm php8.3-cli php8.3-mysql php8.3-xml php8.3-mbstring \
    php8.3-curl php8.3-zip php8.3-gd php8.3-intl php8.3-bcmath \
    php8.3-redis php8.3-common \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true

if ! command -v php8.3 &>/dev/null; then
    for phpv in php8.2 php8.1; do
        v="${phpv#php}"
        apt-get install -y --quiet \
            ${phpv}-fpm ${phpv}-cli ${phpv}-mysql ${phpv}-xml ${phpv}-mbstring \
            ${phpv}-curl ${phpv}-zip ${phpv}-gd ${phpv}-intl ${phpv}-bcmath \
            ${phpv}-redis ${phpv}-common 2>/dev/null && break || true
    done
fi
PHP_BIN=$(which php8.3 2>/dev/null || which php8.2 2>/dev/null || which php8.1 2>/dev/null || which php)
success "PHP: $($PHP_BIN --version | head -1)"

if ! command -v mysql &>/dev/null; then
    apt-get install -y --quiet mariadb-server mariadb-client \
        2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true
    systemctl enable --now mariadb
fi
success "MySQL/MariaDB verfügbar"

# --- System-User ---
if ! id "${MONICA_USER}" &>/dev/null; then
    useradd -r -s /bin/false -d "${MONICA_DIR}" -m "${MONICA_USER}"
    success "System-User '${MONICA_USER}' angelegt"
fi

# --- Datenbank ---
info "Richte Datenbank ein..."
mysql -e "CREATE DATABASE IF NOT EXISTS ${MONICA_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null
mysql -e "CREATE USER IF NOT EXISTS '${MONICA_DB_USER}'@'localhost' IDENTIFIED BY '${MONICA_DB_PASS}';" 2>/dev/null
mysql -e "GRANT ALL PRIVILEGES ON ${MONICA_DB}.* TO '${MONICA_DB_USER}'@'localhost';" 2>/dev/null
mysql -e "FLUSH PRIVILEGES;" 2>/dev/null
success "Datenbank '${MONICA_DB}' bereit"

# --- Monica herunterladen ---
info "Lade Monica herunter..."
MONICA_VERSION=$(curl -sf "https://api.github.com/repos/monicahq/monica/releases/latest" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('tag_name','v4.1.2'))" 2>/dev/null \
    || echo "v4.1.2")
info "Version: ${MONICA_VERSION}"

mkdir -p "${MONICA_DIR}"
curl -fSL "https://github.com/monicahq/monica/releases/download/${MONICA_VERSION}/monica-${MONICA_VERSION}.tar.bz2" \
    -o /tmp/monica.tar.bz2 2>/dev/null \
    || { warn "Release-Archiv nicht gefunden — versuche git clone..."; \
         git clone --depth 1 https://github.com/monicahq/monica.git "${MONICA_DIR}" \
         || die "Monica Download fehlgeschlagen"; }

if [ -f /tmp/monica.tar.bz2 ]; then
    tar -xjf /tmp/monica.tar.bz2 -C "${MONICA_DIR}" --strip-components=1 \
        || { warn "tar fehlgeschlagen — versuche git clone..."; \
             rm -rf "${MONICA_DIR}"; mkdir -p "${MONICA_DIR}"; \
             git clone --depth 1 https://github.com/monicahq/monica.git "${MONICA_DIR}" \
             || die "Monica Download fehlgeschlagen"; }
    rm -f /tmp/monica.tar.bz2
fi

chown -R "${MONICA_USER}:${MONICA_USER}" "${MONICA_DIR}"
success "Monica ${MONICA_VERSION} nach ${MONICA_DIR}"

# --- .env ---
cd "${MONICA_DIR}"
[ -f .env.example ] && sudo -u "${MONICA_USER}" cp .env.example .env || touch .env
chown "${MONICA_USER}:${MONICA_USER}" .env

_SERVER_IP="$(hostname -I | awk '{print $1}')"

cat > "${MONICA_DIR}/.env" << ENVEOF
APP_NAME=Monica
APP_ENV=production
APP_KEY=
APP_DEBUG=false
APP_URL=http://${_SERVER_IP}:${MONICA_PORT}
APP_FORCE_HTTPS=false
APP_TRUSTED_PROXIES=

LOG_CHANNEL=daily

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=${MONICA_DB}
DB_USERNAME=${MONICA_DB_USER}
DB_PASSWORD=${MONICA_DB_PASS}

CACHE_DRIVER=file
SESSION_DRIVER=file
QUEUE_CONNECTION=sync

MAIL_MAILER=log

DEFAULT_MAX_UPLOAD_SIZE=10240
ENVEOF
chown "${MONICA_USER}:${MONICA_USER}" "${MONICA_DIR}/.env"
chmod 600 "${MONICA_DIR}/.env"

cd "${MONICA_DIR}"
sudo -u "${MONICA_USER}" $PHP_BIN artisan key:generate --force --quiet 2>/dev/null \
    || { FALLBACK_KEY="base64:$(head -c 32 /dev/urandom | base64)"; \
         sed -i "s|APP_KEY=|APP_KEY=${FALLBACK_KEY}|" "${MONICA_DIR}/.env"; }
success ".env konfiguriert + App-Key generiert"

# --- HTTPS-Redirect deaktivieren (läuft ohne Reverse-Proxy auf Port) ---
ROUTE_PROVIDER="${MONICA_DIR}/app/Providers/RouteServiceProvider.php"
if [ -f "${ROUTE_PROVIDER}" ]; then
    sed -i "s|URL::forceScheme('https');|// URL::forceScheme('https');|" "${ROUTE_PROVIDER}"
fi

# --- Migration ---
info "Führe Datenbank-Migration aus..."
cd "${MONICA_DIR}"
sudo -u "${MONICA_USER}" $PHP_BIN artisan migrate --force --quiet
sudo -u "${MONICA_USER}" $PHP_BIN artisan storage:link --quiet 2>/dev/null || true
sudo -u "${MONICA_USER}" $PHP_BIN artisan passport:keys --force --quiet 2>/dev/null || true
sudo -u "${MONICA_USER}" $PHP_BIN artisan passport:client --personal --name="HydraHive" \
    --no-interaction --quiet 2>/dev/null || true
success "Datenbank migriert"

# --- systemd Service ---
cat > /etc/systemd/system/monica.service << SVCEOF
[Unit]
Description=Monica CRM
After=network.target mariadb.service

[Service]
Type=simple
User=${MONICA_USER}
Group=${MONICA_USER}
WorkingDirectory=${MONICA_DIR}
ExecStart=${PHP_BIN} artisan serve --host=0.0.0.0 --port=${MONICA_PORT}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable --now monica
success "systemd Service 'monica' gestartet auf Port ${MONICA_PORT}"

# --- Warten ---
info "Warte auf Monica..."
for i in $(seq 1 15); do
    sleep 2
    curl -sf "http://127.0.0.1:${MONICA_PORT}" &>/dev/null && break || true
done
curl -sf "http://127.0.0.1:${MONICA_PORT}" &>/dev/null \
    && success "Monica läuft auf http://127.0.0.1:${MONICA_PORT}" \
    || warn "Monica startet noch — prüfe: systemctl status monica"

# --- Credentials ---
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/monica-crm.credentials.json << CREDEOF
{
  "id": "monica-crm",
  "name": "Monica CRM",
  "fields": [
    {"label": "URL",         "value": "http://127.0.0.1:${MONICA_PORT}", "secret": false},
    {"label": "DB-Passwort", "value": "${MONICA_DB_PASS}",               "secret": true}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/monica-crm.credentials.json
chmod 640 /etc/hydrahive2/extensions/monica-crm.credentials.json

success "Monica CRM installiert"
info "  URL:    http://127.0.0.1:${MONICA_PORT}"
info "  Ersten Account auf der Weboberfläche anlegen"
