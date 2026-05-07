#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

MAILCOW_DIR="/opt/mailcow-dockerized"
MAILCOW_CONF="${MAILCOW_DIR}/mailcow.conf"
MAILCOW_HOSTNAME="${MAILCOW_HOSTNAME:-mail.hydrahive.local}"
MAILCOW_TZ="${MAILCOW_TZ:-Europe/Berlin}"
MAILCOW_DBPASS="${MAILCOW_DBPASS:-$(openssl rand -hex 32)}"

# HTTP/HTTPS auf nicht-standard Ports damit kein Konflikt mit bestehendem nginx
HTTP_PORT="${HTTP_PORT:-8180}"
HTTPS_PORT="${HTTPS_PORT:-8543}"

info "Installiere Mailcow — Hostname: ${MAILCOW_HOSTNAME}"

# ── Abhängigkeiten ───────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    die "Docker ist nicht installiert. Bitte zuerst Docker installieren."
fi
if ! docker compose version &>/dev/null 2>&1; then
    die "Docker Compose (Plugin) ist nicht verfügbar."
fi

# ── Mailcow klonen ───────────────────────────────────────────────────────────
if [ -d "${MAILCOW_DIR}/.git" ]; then
    info "Mailcow bereits geklont — aktualisiere..."
    git -C "${MAILCOW_DIR}" fetch --quiet
    git -C "${MAILCOW_DIR}" pull --quiet
else
    info "Klone Mailcow..."
    git clone --depth=1 https://github.com/mailcow/mailcow-dockerized.git "${MAILCOW_DIR}"
    success "Mailcow geklont"
fi

# ── Konfiguration ─────────────────────────────────────────────────────────────
if [ -f "${MAILCOW_CONF}" ]; then
    info "mailcow.conf bereits vorhanden — überspringe Generierung"
else
    info "Generiere mailcow.conf..."
    cd "${MAILCOW_DIR}"
    # generate_config.sh liest MAILCOW_HOSTNAME und MAILCOW_TZ aus Umgebung
    MAILCOW_HOSTNAME="${MAILCOW_HOSTNAME}" \
    MAILCOW_TZ="${MAILCOW_TZ}" \
    bash generate_config.sh

    # Ports anpassen (kein Konflikt mit bestehendem nginx/80/443)
    sed -i "s/^HTTP_PORT=.*/HTTP_PORT=${HTTP_PORT}/" "${MAILCOW_CONF}"
    sed -i "s/^HTTPS_PORT=.*/HTTPS_PORT=${HTTPS_PORT}/" "${MAILCOW_CONF}"

    # Datenbankpasswort setzen
    sed -i "s/^DBPASS=.*/DBPASS=${MAILCOW_DBPASS}/" "${MAILCOW_CONF}"

    success "mailcow.conf generiert (HTTP: ${HTTP_PORT}, HTTPS: ${HTTPS_PORT})"
fi

# ── Starten ──────────────────────────────────────────────────────────────────
info "Starte Mailcow-Stack (kann einige Minuten dauern)..."
cd "${MAILCOW_DIR}"
docker compose pull --quiet
docker compose up -d
success "Mailcow-Stack gestartet"

# ── Warten bis UI erreichbar ─────────────────────────────────────────────────
info "Warte auf Mailcow-UI..."
for i in $(seq 1 30); do
    if curl -sf --max-time 5 "http://127.0.0.1:${HTTP_PORT}/" &>/dev/null; then
        success "Mailcow erreichbar auf http://127.0.0.1:${HTTP_PORT}"
        break
    fi
    echo -n "."
    sleep 10
done

# ── Credentials speichern ─────────────────────────────────────────────────────
mkdir -p /etc/hydrahive2/extensions
ADMIN_PASS=$(grep "^DBPASS=" "${MAILCOW_CONF}" | cut -d= -f2 || echo "${MAILCOW_DBPASS}")
cat > /etc/hydrahive2/extensions/mailcow.credentials.json << CREDFILE
{
  "id": "mailcow",
  "name": "Mailcow (Mail-Server)",
  "fields": [
    {"label": "URL", "value": "http://$(hostname -I | awk '{print $1}'):${HTTP_PORT}", "secret": false},
    {"label": "Admin-Login", "value": "admin", "secret": false},
    {"label": "Admin-Passwort", "value": "moohoo", "secret": true},
    {"label": "Hostname", "value": "${MAILCOW_HOSTNAME}", "secret": false},
    {"label": "DB-Passwort", "value": "${MAILCOW_DBPASS}", "secret": true}
  ]
}
CREDFILE
chown root:hydrahive /etc/hydrahive2/extensions/mailcow.credentials.json
chmod 640 /etc/hydrahive2/extensions/mailcow.credentials.json

success "Mailcow installiert"
info "  UI:              http://$(hostname -I | awk '{print $1}'):${HTTP_PORT}"
info "  Admin-Login:     admin / moohoo"
info "  Passwort SOFORT nach Login ändern!"
info "  Fetchmail:       Konfiguration unter Mail-Setup → Fetchmail"
info "  Weitere Domains: Mail-Setup → Domains"
