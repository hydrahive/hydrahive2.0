#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

BS_DIR="/opt/bookstack"
BS_USER="bookstack"
BS_DB="bookstack"
BS_DB_USER="bookstack"
BS_DB_PASS="$(head -c 16 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 24)"
BS_PORT="8500"

info "Installiere BookStack..."

_SERVER_IP="$(hostname -I | awk '{print $1}')"

detect_php() {
    for v in 8.3 8.2 8.1 8.0; do
        command -v "php${v}" &>/dev/null && echo "${v}" && return
    done
    command -v php &>/dev/null && php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;' && return
    echo ""
}

# --- Abhängigkeiten ---
info "Installiere Abhängigkeiten (PHP, MariaDB, Composer, git)..."
apt-get update -qq
apt-get install -y --quiet \
    php-cli php-mysql php-curl php-xml php-mbstring \
    php-gd php-zip php-intl php-ldap php-tokenizer \
    mariadb-server mariadb-client \
    git curl unzip \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true

PHP_VERSION="$(detect_php)"
[ -n "${PHP_VERSION}" ] || die "Keine PHP-Version gefunden nach Installation"
success "PHP ${PHP_VERSION} erkannt"

if ! command -v composer &>/dev/null; then
    info "Installiere Composer..."
    curl -fsSL https://getcomposer.org/installer -o /tmp/composer-setup.php
    php /tmp/composer-setup.php --install-dir=/usr/local/bin --filename=composer --quiet
    rm -f /tmp/composer-setup.php
    success "Composer installiert"
fi

systemctl enable --now mariadb

# --- System-User ---
if ! id "${BS_USER}" &>/dev/null; then
    if getent group "${BS_USER}" &>/dev/null; then
        useradd -r -s /bin/false -d "${BS_DIR}" -g "${BS_USER}" "${BS_USER}"
    else
        useradd -r -s /bin/false -d "${BS_DIR}" "${BS_USER}"
    fi
    success "System-User '${BS_USER}' angelegt"
fi
usermod -aG "${BS_USER}" www-data 2>/dev/null || true

# --- BookStack herunterladen / aktualisieren ---
if [ -d "${BS_DIR}/.git" ]; then
    info "BookStack bereits geklont — aktualisiere..."
    systemctl stop bookstack bookstack-queue 2>/dev/null || true
    git -C "${BS_DIR}" fetch --quiet origin
    git -C "${BS_DIR}" reset --hard origin/release --quiet 2>/dev/null \
        || git -C "${BS_DIR}" reset --hard origin/main --quiet
    chown -R "${BS_USER}:${BS_USER}" "${BS_DIR}"
    sudo -u "${BS_USER}" composer install \
        --no-dev --no-interaction --quiet \
        --working-dir="${BS_DIR}" 2>/dev/null || true
    sudo -u "${BS_USER}" php "${BS_DIR}/artisan" migrate --force --quiet 2>/dev/null || true
    systemctl start bookstack bookstack-queue 2>/dev/null || true
    success "BookStack aktualisiert"
    exit 0
fi

info "Klone BookStack von GitHub..."
rm -rf "${BS_DIR}"
git clone --depth 1 --branch release \
    https://github.com/BookStackApp/BookStack.git "${BS_DIR}" \
    || git clone --depth 1 \
        https://github.com/BookStackApp/BookStack.git "${BS_DIR}" \
    || die "git clone fehlgeschlagen"
success "BookStack geklont"

# --- Datenbank ---
info "Richte Datenbank ein..."
mysql -e "CREATE DATABASE IF NOT EXISTS ${BS_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null
mysql -e "CREATE USER IF NOT EXISTS '${BS_DB_USER}'@'localhost' IDENTIFIED BY '${BS_DB_PASS}';" 2>/dev/null
mysql -e "GRANT ALL PRIVILEGES ON ${BS_DB}.* TO '${BS_DB_USER}'@'localhost';" 2>/dev/null
mysql -e "FLUSH PRIVILEGES;" 2>/dev/null
success "Datenbank '${BS_DB}' bereit"

# --- .env ---
cat > "${BS_DIR}/.env" << ENVEOF
APP_NAME=BookStack
APP_ENV=production
APP_KEY=
APP_DEBUG=false
APP_URL=http://${_SERVER_IP}:${BS_PORT}

LOG_CHANNEL=daily

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=${BS_DB}
DB_USERNAME=${BS_DB_USER}
DB_PASSWORD=${BS_DB_PASS}

CACHE_DRIVER=file
SESSION_DRIVER=file
QUEUE_CONNECTION=sync

MAIL_DRIVER=log
ENVEOF
chown "${BS_USER}:${BS_USER}" "${BS_DIR}/.env"
chmod 640 "${BS_DIR}/.env"

# --- Composer ---
info "Installiere PHP-Abhängigkeiten via Composer..."
chown -R "${BS_USER}:${BS_USER}" "${BS_DIR}"
sudo -u "${BS_USER}" composer install \
    --no-dev --no-interaction --quiet \
    --working-dir="${BS_DIR}" 2>/dev/null \
    || warn "composer install hatte Fehler — BookStack läuft ggf. trotzdem"

# --- App-Key ---
php "${BS_DIR}/artisan" key:generate --force --quiet 2>/dev/null \
    || { FALLBACK_KEY="base64:$(head -c 32 /dev/urandom | base64)"; \
         sed -i "s|APP_KEY=|APP_KEY=${FALLBACK_KEY}|" "${BS_DIR}/.env"; }
success "App-Key generiert"

# --- Storage ---
mkdir -p "${BS_DIR}/storage/framework"/{sessions,views,cache} \
         "${BS_DIR}/storage/uploads"/{images,files,drawio} \
         "${BS_DIR}/bootstrap/cache"
php "${BS_DIR}/artisan" storage:link --quiet 2>/dev/null || true

# --- Migration ---
info "Führe Datenbank-Migration aus..."
php "${BS_DIR}/artisan" migrate --force --quiet \
    || warn "Migration fehlgeschlagen — beim ersten Aufruf wiederholt"

# --- Berechtigungen ---
chown -R "${BS_USER}:${BS_USER}" "${BS_DIR}"
chmod -R 755 "${BS_DIR}/storage" "${BS_DIR}/bootstrap/cache" 2>/dev/null || true
success "Berechtigungen gesetzt"

PHP_BIN="$(command -v "php${PHP_VERSION}" 2>/dev/null || command -v php)"

# --- systemd Services ---
cat > /etc/systemd/system/bookstack.service << SVCEOF
[Unit]
Description=BookStack Wiki
After=network.target mariadb.service

[Service]
Type=simple
User=${BS_USER}
Group=${BS_USER}
WorkingDirectory=${BS_DIR}
ExecStart=${PHP_BIN} artisan serve --host=0.0.0.0 --port=${BS_PORT}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

cat > /etc/systemd/system/bookstack-queue.service << SVCEOF
[Unit]
Description=BookStack Queue Worker
After=network.target mariadb.service
Requires=mariadb.service

[Service]
Type=simple
User=${BS_USER}
Group=${BS_USER}
WorkingDirectory=${BS_DIR}
ExecStart=${PHP_BIN} artisan queue:work --queue=default --sleep=3 --tries=3 --timeout=90
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable --now bookstack bookstack-queue
success "Services 'bookstack' + 'bookstack-queue' gestartet"

# --- Warten ---
info "Warte auf BookStack (bis 30 s)..."
for i in $(seq 1 15); do
    sleep 2
    curl -sf "http://127.0.0.1:${BS_PORT}" &>/dev/null && break || true
done
curl -sf "http://127.0.0.1:${BS_PORT}" &>/dev/null \
    && success "BookStack erreichbar" \
    || warn "BookStack noch nicht erreichbar — prüfe: journalctl -u bookstack"

# --- Credentials ---
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/bookstack.credentials.json << CREDEOF
{
  "id": "bookstack",
  "name": "BookStack (Wiki/Dokumentation)",
  "fields": [
    {"label": "URL",           "value": "http://${_SERVER_IP}:${BS_PORT}", "secret": false},
    {"label": "Login",         "value": "admin@admin.com",                 "secret": false},
    {"label": "Passwort",      "value": "password",                        "secret": true},
    {"label": "DB-Passwort",   "value": "${BS_DB_PASS}",                   "secret": true}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/bookstack.credentials.json
chmod 640 /etc/hydrahive2/extensions/bookstack.credentials.json

success "BookStack installiert"
info "  URL:    http://${_SERVER_IP}:${BS_PORT}"
info "  Login:  admin@admin.com / password"
warn "  Passwort sofort nach dem ersten Login ändern!"
