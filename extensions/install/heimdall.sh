#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

HEIMDALL_DIR="/opt/heimdall"
HEIMDALL_USER="heimdall"
HEIMDALL_PORT="8400"
NGINX_CONF="/etc/nginx/sites-available/heimdall"
NGINX_ENABLED="/etc/nginx/sites-enabled/heimdall"

info "Installiere Heimdall..."

detect_php() {
    for v in 8.3 8.2 8.1 8.0; do
        command -v "php${v}" &>/dev/null && echo "${v}" && return
    done
    command -v php &>/dev/null && php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;' && return
    echo ""
}

# --- Abhängigkeiten ---
info "Installiere Abhängigkeiten (PHP, nginx, SQLite3, Composer)..."
apt-get update -qq
apt-get install -y --quiet \
    php-fpm php-cli php-sqlite3 php-curl php-xml php-mbstring \
    php-gd php-zip php-intl php-bcmath php-tokenizer \
    nginx git curl sqlite3 \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true

export COMPOSER_HOME=/tmp/composer-home
mkdir -p "$COMPOSER_HOME"

if ! command -v composer &>/dev/null; then
    info "Installiere Composer..."
    curl -fsSL https://getcomposer.org/installer -o /tmp/composer-setup.php
    php /tmp/composer-setup.php --install-dir=/usr/local/bin --filename=composer --quiet
    rm -f /tmp/composer-setup.php
    success "Composer installiert"
fi

PHP_VERSION="$(detect_php)"
[ -n "${PHP_VERSION}" ] || die "Keine PHP-Version gefunden"
PHP_FPM_SERVICE="php${PHP_VERSION}-fpm"
success "PHP ${PHP_VERSION} erkannt"

# --- System-User ---
if ! id "${HEIMDALL_USER}" &>/dev/null; then
    if getent group "${HEIMDALL_USER}" &>/dev/null; then
        useradd -r -s /bin/false -d "${HEIMDALL_DIR}" -g "${HEIMDALL_USER}" "${HEIMDALL_USER}"
    else
        useradd -r -s /bin/false -d "${HEIMDALL_DIR}" "${HEIMDALL_USER}"
    fi
    success "System-User '${HEIMDALL_USER}' angelegt"
fi
usermod -aG "${HEIMDALL_USER}" www-data 2>/dev/null || true

# --- Heimdall herunterladen / aktualisieren ---
if [ -d "${HEIMDALL_DIR}/.git" ]; then
    info "Heimdall bereits geklont — aktualisiere..."
    git -C "${HEIMDALL_DIR}" fetch --quiet origin
    git -C "${HEIMDALL_DIR}" reset --hard origin/master --quiet 2>/dev/null \
        || git -C "${HEIMDALL_DIR}" reset --hard origin/main --quiet
    sudo -u "${HEIMDALL_USER}" COMPOSER_HOME=/tmp/composer-home composer install \
        --no-dev --no-interaction --quiet \
        --working-dir="${HEIMDALL_DIR}" 2>/dev/null || true
    success "Heimdall aktualisiert"
else
    info "Klone Heimdall von GitHub..."
    rm -rf "${HEIMDALL_DIR}"
    git clone --depth 1 https://github.com/linuxserver/Heimdall.git "${HEIMDALL_DIR}" \
        || die "git clone fehlgeschlagen"
    success "Heimdall geklont"
    info "Installiere PHP-Abhängigkeiten..."
    COMPOSER_HOME=/tmp/composer-home composer install \
        --no-dev --no-interaction --quiet \
        --working-dir="${HEIMDALL_DIR}" 2>/dev/null \
        || warn "composer install hatte Fehler"
fi

# --- .env ---
_SERVER_IP=$(hostname -I | awk '{print $1}')
if [ ! -f "${HEIMDALL_DIR}/.env" ]; then
    cp "${HEIMDALL_DIR}/.env.example" "${HEIMDALL_DIR}/.env" 2>/dev/null \
        || cat > "${HEIMDALL_DIR}/.env" << ENVEOF
APP_NAME=Heimdall
APP_ENV=production
APP_KEY=
APP_DEBUG=false
APP_URL=http://${_SERVER_IP}:${HEIMDALL_PORT}
DB_CONNECTION=sqlite
DB_DATABASE=${HEIMDALL_DIR}/database/app.sqlite
LOG_CHANNEL=daily
CACHE_DRIVER=file
SESSION_DRIVER=file
QUEUE_CONNECTION=sync
ENVEOF
fi
sed -i "s|^APP_URL=.*|APP_URL=http://${_SERVER_IP}:${HEIMDALL_PORT}|" "${HEIMDALL_DIR}/.env"
sed -i "s|^APP_ENV=.*|APP_ENV=production|" "${HEIMDALL_DIR}/.env"

if grep -q "^APP_KEY=$" "${HEIMDALL_DIR}/.env" || grep -q "^APP_KEY=SomeRandomString" "${HEIMDALL_DIR}/.env"; then
    php "${HEIMDALL_DIR}/artisan" key:generate --force --quiet 2>/dev/null || true
fi

# --- Datenbank + Storage ---
mkdir -p "${HEIMDALL_DIR}/database" "${HEIMDALL_DIR}/storage/framework"/{sessions,views,cache}
touch "${HEIMDALL_DIR}/database/app.sqlite" 2>/dev/null || true
php "${HEIMDALL_DIR}/artisan" migrate --force --quiet 2>/dev/null \
    || warn "Migration fehlgeschlagen"
php "${HEIMDALL_DIR}/artisan" storage:link --quiet 2>/dev/null || true

# --- Berechtigungen ---
chown -R "${HEIMDALL_USER}:${HEIMDALL_USER}" "${HEIMDALL_DIR}"
chmod -R 755 "${HEIMDALL_DIR}/storage" "${HEIMDALL_DIR}/bootstrap/cache" 2>/dev/null || true
chmod 664 "${HEIMDALL_DIR}/database/app.sqlite" 2>/dev/null || true
success "Berechtigungen gesetzt"

# --- PHP-FPM Pool ---
PHP_FPM_SOCK="/run/php/heimdall-fpm.sock"
PHP_POOL_DIR="/etc/php/${PHP_VERSION}/fpm/pool.d"
if [ -d "${PHP_POOL_DIR}" ]; then
    cat > "${PHP_POOL_DIR}/heimdall.conf" << POOLEOF
[heimdall]
user = ${HEIMDALL_USER}
group = ${HEIMDALL_USER}
listen = ${PHP_FPM_SOCK}
listen.owner = www-data
listen.group = www-data
listen.mode = 0660
pm = dynamic
pm.max_children = 10
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
pm.max_requests = 500
chdir = /
POOLEOF
    systemctl restart "${PHP_FPM_SERVICE}" 2>/dev/null || true
    success "PHP-FPM Pool 'heimdall' konfiguriert"
else
    PHP_FPM_SOCK="/run/php/php${PHP_VERSION}-fpm.sock"
    warn "PHP-FPM Pool-Verzeichnis nicht gefunden — nutze Standard-Socket"
fi

# --- nginx ---
info "Konfiguriere nginx (Port ${HEIMDALL_PORT})..."
cat > "${NGINX_CONF}" << NGXEOF
server {
    listen 0.0.0.0:${HEIMDALL_PORT};
    server_name _;

    root ${HEIMDALL_DIR}/public;
    index index.php;

    access_log /var/log/nginx/heimdall-access.log;
    error_log  /var/log/nginx/heimdall-error.log;

    location / {
        try_files \$uri \$uri/ /index.php?\$query_string;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:${PHP_FPM_SOCK};
        fastcgi_param SCRIPT_FILENAME \$realpath_root\$fastcgi_script_name;
        include fastcgi_params;
        fastcgi_read_timeout 120;
    }

    location ~ /\.(?!well-known) {
        deny all;
    }

    client_max_body_size 64M;
}
NGXEOF
ln -sf "${NGINX_CONF}" "${NGINX_ENABLED}" 2>/dev/null || true
nginx -t 2>/dev/null && systemctl reload nginx \
    || warn "nginx-Konfigurationstest fehlgeschlagen"
success "nginx konfiguriert"

# --- systemd Queue-Worker ---
cat > /etc/systemd/system/heimdall.service << SVCEOF
[Unit]
Description=Heimdall App Dashboard Queue Worker
After=network.target nginx.service ${PHP_FPM_SERVICE}.service
Requires=${PHP_FPM_SERVICE}.service

[Service]
Type=simple
User=${HEIMDALL_USER}
Group=${HEIMDALL_USER}
WorkingDirectory=${HEIMDALL_DIR}
ExecStart=/usr/bin/php artisan queue:work --queue=default --sleep=3 --tries=3 --timeout=90
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable nginx "${PHP_FPM_SERVICE}" heimdall
systemctl start "${PHP_FPM_SERVICE}" heimdall
systemctl reload nginx 2>/dev/null || systemctl start nginx
success "Alle Services gestartet"

# --- Warten ---
info "Warte auf Heimdall (bis 20 s)..."
for i in $(seq 1 10); do
    sleep 2
    curl -sf "http://127.0.0.1:${HEIMDALL_PORT}" &>/dev/null && break || true
done
curl -sf "http://127.0.0.1:${HEIMDALL_PORT}" &>/dev/null \
    && success "Heimdall erreichbar" \
    || warn "Heimdall noch nicht erreichbar — prüfe nginx + PHP-FPM"

success "Heimdall installiert"
info "  URL:    http://${_SERVER_IP}:${HEIMDALL_PORT}"
info "  Kein Standard-Login — Registrierung direkt im Browser"
