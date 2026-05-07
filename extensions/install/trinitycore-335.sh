#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

TC_DIR="/opt/trinitycore-335"
TC_USER="trinity335"
TC_SOURCE="${TC_DIR}/source"
TC_BUILD="${TC_DIR}/build"
TC_SERVER="${TC_DIR}/server"
TC_DATA="${TC_DIR}/data"
WORLD_PORT="8085"
AUTH_PORT="3724"
DB_USER="trinity335"
DB_PASS="trinity335_$(hostname | md5sum | head -c8)"
CORES=$(nproc)

info "Installiere TrinityCore 3.3.5a (WotLK) — ${CORES} CPU-Kerne"

# --- System-User ---
if ! id "${TC_USER}" &>/dev/null; then
    useradd -r -m -d "${TC_DIR}" -s /bin/bash "${TC_USER}"
    success "User '${TC_USER}' erstellt"
fi
mkdir -p "${TC_DIR}" "${TC_SOURCE}" "${TC_BUILD}" "${TC_SERVER}" "${TC_DATA}"

# --- Build-Dependencies ---
info "Installiere Build-Dependencies..."
apt-get update -qq 2>&1 | tail -1
apt-get install -y -qq \
    git clang cmake make gcc g++ \
    libmysqlclient-dev libssl-dev libbz2-dev libreadline-dev \
    libncurses-dev libboost-all-dev libfmt-dev \
    mysql-server p7zip-full \
    2>&1 | tail -3
success "Build-Dependencies installiert"

# --- MySQL/MariaDB ---
info "Konfiguriere Datenbank..."
if systemctl is-active mariadb &>/dev/null; then
    info "MariaDB läuft bereits"
elif systemctl start mysql 2>/dev/null; then
    systemctl enable mysql 2>/dev/null || true
    info "MySQL gestartet"
elif systemctl start mariadb 2>/dev/null; then
    systemctl enable mariadb 2>/dev/null || true
    info "MariaDB gestartet"
else
    warn "MySQL/MariaDB nicht startbar — installiere MariaDB..."
    apt-get install -y -qq mariadb-server 2>&1 | tail -3
    systemctl start mariadb
    systemctl enable mariadb 2>/dev/null || true
    success "MariaDB installiert"
fi

mysql -u root -e "
    CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
    CREATE DATABASE IF NOT EXISTS trinity335_auth;
    CREATE DATABASE IF NOT EXISTS trinity335_characters;
    CREATE DATABASE IF NOT EXISTS trinity335_world;
    GRANT ALL PRIVILEGES ON trinity335_auth.* TO '${DB_USER}'@'localhost';
    GRANT ALL PRIVILEGES ON trinity335_characters.* TO '${DB_USER}'@'localhost';
    GRANT ALL PRIVILEGES ON trinity335_world.* TO '${DB_USER}'@'localhost';
    FLUSH PRIVILEGES;
" 2>/dev/null || warn "MySQL User/DB Setup — evtl. bereits vorhanden"
success "MySQL: Datenbanken trinity335_auth/characters/world bereit"

# --- Source klonen / aktualisieren ---
if [ ! -d "${TC_SOURCE}/.git" ]; then
    info "Klone TrinityCore 3.3.5 Source (kann dauern)..."
    git clone --branch 3.3.5 --depth 1 \
        https://github.com/TrinityCore/TrinityCore.git "${TC_SOURCE}" 2>&1 | tail -3
    success "Source geklont"
else
    info "Aktualisiere Source..."
    cd "${TC_SOURCE}" && git pull --ff-only 2>&1 | tail -3
    success "Source aktualisiert"
fi

# --- Kompilieren ---
info "Kompiliere TrinityCore (${CORES} Kerne, kann 15-30 Min dauern)..."
cd "${TC_BUILD}"
cmake "${TC_SOURCE}" \
    -DCMAKE_INSTALL_PREFIX="${TC_SERVER}" \
    -DCMAKE_C_COMPILER=/usr/bin/clang \
    -DCMAKE_CXX_COMPILER=/usr/bin/clang++ \
    -DTOOLS=1 \
    -DWITH_WARNINGS=0 \
    2>&1 | tail -5
make -j${CORES} 2>&1 | tail -10
make install 2>&1 | tail -5
success "Kompilierung abgeschlossen"

# --- Konfiguration ---
if [ ! -f "${TC_SERVER}/etc/worldserver.conf" ]; then
    cp "${TC_SERVER}/etc/worldserver.conf.dist" "${TC_SERVER}/etc/worldserver.conf"
    cp "${TC_SERVER}/etc/authserver.conf.dist" "${TC_SERVER}/etc/authserver.conf"
    sed -i "s|LoginDatabaseInfo.*=.*|LoginDatabaseInfo = \"127.0.0.1;3306;${DB_USER};${DB_PASS};trinity335_auth\"|" \
        "${TC_SERVER}/etc/worldserver.conf" "${TC_SERVER}/etc/authserver.conf"
    sed -i "s|WorldDatabaseInfo.*=.*|WorldDatabaseInfo = \"127.0.0.1;3306;${DB_USER};${DB_PASS};trinity335_world\"|" \
        "${TC_SERVER}/etc/worldserver.conf"
    sed -i "s|CharacterDatabaseInfo.*=.*|CharacterDatabaseInfo = \"127.0.0.1;3306;${DB_USER};${DB_PASS};trinity335_characters\"|" \
        "${TC_SERVER}/etc/worldserver.conf"
    sed -i "s|DataDir.*=.*|DataDir = \"${TC_DATA}\"|" "${TC_SERVER}/etc/worldserver.conf"
    success "Konfiguration erstellt"
else
    success "Konfiguration bereits vorhanden"
fi

# --- SQL importieren ---
info "Importiere Datenbank-Schemas..."
if [ -d "${TC_SOURCE}/sql/base" ]; then
    for sql in "${TC_SOURCE}/sql/base/"*.sql; do
        [ -f "$sql" ] || continue
        db_name=$(basename "$sql" | grep -oP '(auth|characters|world)' || echo "")
        if [ -n "$db_name" ]; then
            mysql -u "${DB_USER}" -p"${DB_PASS}" "trinity335_${db_name}" < "$sql" 2>/dev/null || true
        fi
    done
    success "Datenbank-Schemas importiert"
fi

chown -R "${TC_USER}:${TC_USER}" "${TC_DIR}"

# --- Firewall ---
if command -v ufw &>/dev/null; then
    ufw allow ${WORLD_PORT}/tcp comment "TrinityCore 335 World" 2>/dev/null || true
    ufw allow ${AUTH_PORT}/tcp comment "TrinityCore 335 Auth" 2>/dev/null || true
    success "Firewall: Port ${WORLD_PORT}/tcp + ${AUTH_PORT}/tcp geöffnet"
fi

# --- systemd Services ---
cat > /etc/systemd/system/trinitycore-335-auth.service << SVCEOF
[Unit]
Description=TrinityCore 3.3.5a Auth Server
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=simple
User=${TC_USER}
WorkingDirectory=${TC_SERVER}/bin
ExecStart=${TC_SERVER}/bin/authserver
Restart=on-failure
RestartSec=15
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

cat > /etc/systemd/system/trinitycore-335-world.service << SVCEOF
[Unit]
Description=TrinityCore 3.3.5a World Server
After=network.target mysql.service trinitycore-335-auth.service
Requires=mysql.service

[Service]
Type=simple
User=${TC_USER}
WorkingDirectory=${TC_SERVER}/bin
ExecStart=${TC_SERVER}/bin/worldserver
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable trinitycore-335-auth trinitycore-335-world 2>/dev/null || true
success "systemd Services registriert"

# Nur starten wenn Map-Daten vorhanden
if [ -d "${TC_DATA}/dbc" ] || [ -d "${TC_DATA}/maps" ]; then
    systemctl start trinitycore-335-auth 2>/dev/null || warn "Auth Server Start fehlgeschlagen"
    systemctl start trinitycore-335-world 2>/dev/null || warn "World Server Start fehlgeschlagen"
    success "Server gestartet"
else
    warn "Map-Daten fehlen — Server kann noch nicht starten!"
fi

# --- Credentials ---
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/trinitycore-335.credentials.json << CREDEOF
{
  "id": "trinitycore-335",
  "name": "TrinityCore 3.3.5a (WotLK)",
  "fields": [
    {"label": "Auth-Port",   "value": "${AUTH_PORT}/tcp",   "secret": false},
    {"label": "World-Port",  "value": "${WORLD_PORT}/tcp",  "secret": false},
    {"label": "DB-User",     "value": "${DB_USER}",         "secret": false},
    {"label": "DB-Passwort", "value": "${DB_PASS}",         "secret": true},
    {"label": "Data-Verz.",  "value": "${TC_DATA}",         "secret": false}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/trinitycore-335.credentials.json
chmod 640 /etc/hydrahive2/extensions/trinitycore-335.credentials.json

success "TrinityCore 3.3.5a installiert"
info "  Auth Server: Port ${AUTH_PORT}/tcp"
info "  World Server: Port ${WORLD_PORT}/tcp"
if [ ! -d "${TC_DATA}/maps" ]; then
    warn "═══════════════════════════════════════════════════════════════"
    warn "  WICHTIG: Map-Daten müssen noch extrahiert werden!"
    warn "  1. WoW 3.3.5a Client auf einem PC haben"
    warn "  2. Map-Extractor: ${TC_SERVER}/bin/mapextractor"
    warn "  3. Extrahierte Daten nach ${TC_DATA}/ kopieren:"
    warn "     dbc/ maps/ vmaps/ mmaps/"
    warn "  4. sudo systemctl start trinitycore-335-world"
    warn "═══════════════════════════════════════════════════════════════"
fi
