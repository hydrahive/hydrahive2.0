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

info "Installiere Mailcow — Hostname: ${MAILCOW_HOSTNAME}"

# ── Abhängigkeiten ───────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    die "Docker ist nicht installiert. Bitte zuerst Docker installieren."
fi
if ! docker compose version &>/dev/null 2>&1; then
    die "Docker Compose (Plugin) ist nicht verfügbar."
fi
if ! command -v jq &>/dev/null; then
    info "Installiere jq..."
    apt-get install -y -qq jq
    success "jq installiert"
fi

# ── Netzwerk-Interface automatisch erkennen ──────────────────────────────────
IFACE=$(ip route | awk '/^default/ {print $5; exit}')
GATEWAY=$(ip route | awk '/^default/ {print $3; exit}')
HOST_IP=$(ip -o -f inet addr show "${IFACE}" | awk 'NR==1{split($4,a,"/"); print a[1]}')
IFS='.' read -r _o1 _o2 _o3 _o4 <<< "${HOST_IP}"
SUBNET="${_o1}.${_o2}.${_o3}.0/24"
info "Netzwerk: Interface=${IFACE}, Gateway=${GATEWAY}, Subnet=${SUBNET}"

# Freie IP im Bereich .200–.250 suchen (außerhalb typischer DHCP-Pools)
MAILCOW_IP=""
for last in $(seq 200 250); do
    candidate="${_o1}.${_o2}.${_o3}.${last}"
    [ "${candidate}" = "${HOST_IP}" ] && continue
    if ! ping -c1 -W1 -q "${candidate}" &>/dev/null 2>&1; then
        if ! arp -n 2>/dev/null | grep -q "^${candidate}[[:space:]]"; then
            MAILCOW_IP="${candidate}"
            break
        fi
    fi
done
[ -z "${MAILCOW_IP}" ] && die "Keine freie IP im Bereich ${_o1}.${_o2}.${_o3}.200-250 gefunden"
info "Mailcow-IP: ${MAILCOW_IP}"

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
    MAILCOW_HOSTNAME="${MAILCOW_HOSTNAME}" \
    MAILCOW_TZ="${MAILCOW_TZ}" \
    bash generate_config.sh
    sed -i "s/^DBPASS=.*/DBPASS=${MAILCOW_DBPASS}/" "${MAILCOW_CONF}"
    success "mailcow.conf generiert"
fi

# ── Macvlan-Netzwerk anlegen ─────────────────────────────────────────────────
# Mailcow bekommt eine eigene LAN-IP — kein Port-Conflict, kein Redirect-Problem.
MACVLAN_NET="mailcow-macvlan"
if ! docker network inspect "${MACVLAN_NET}" &>/dev/null 2>&1; then
    docker network create \
        --driver macvlan \
        --subnet="${SUBNET}" \
        --gateway="${GATEWAY}" \
        --opt parent="${IFACE}" \
        "${MACVLAN_NET}"
    success "macvlan-Netzwerk ${MACVLAN_NET} erstellt"
else
    info "macvlan-Netzwerk ${MACVLAN_NET} bereits vorhanden"
fi

# ── Docker-Compose-Override ──────────────────────────────────────────────────
# nginx-mailcow bekommt die dedizierte LAN-IP über macvlan.
# watchdog bekommt sysctls:[] — Fix für LXC/VM-Umgebungen.
cat > "${MAILCOW_DIR}/docker-compose.override.yml" << OVERRIDE
networks:
  mailcow-macvlan:
    external: true
    name: ${MACVLAN_NET}

services:
  nginx-mailcow:
    networks:
      mailcow-network: {}
      mailcow-macvlan:
        ipv4_address: "${MAILCOW_IP}"
  watchdog-mailcow:
    sysctls: []
OVERRIDE
success "docker-compose.override.yml erstellt (IP: ${MAILCOW_IP})"

# ── Kernel-Sysctl (Host-seitig, best-effort) ─────────────────────────────────
if sysctl -w net.ipv4.ip_unprivileged_port_start=0 &>/dev/null 2>&1; then
    grep -q "ip_unprivileged_port_start" /etc/sysctl.conf || \
        echo "net.ipv4.ip_unprivileged_port_start=0" >> /etc/sysctl.conf
fi

# ── Starten ──────────────────────────────────────────────────────────────────
info "Starte Mailcow-Stack (kann einige Minuten dauern)..."
cd "${MAILCOW_DIR}"
docker compose pull --quiet
docker compose up -d
success "Mailcow-Stack gestartet"

# ── Warten bis UI erreichbar ─────────────────────────────────────────────────
info "Warte auf Mailcow-UI (${MAILCOW_IP})..."
for i in $(seq 1 30); do
    if curl -sf --max-time 5 "http://${MAILCOW_IP}/" &>/dev/null; then
        success "Mailcow erreichbar auf http://${MAILCOW_IP}"
        break
    fi
    echo -n "."
    sleep 10
done

# ── URL + Credentials speichern ───────────────────────────────────────────────
mkdir -p /etc/hydrahive2/extensions

# URL-Datei — wird vom Extension-Status als open_url verwendet
echo "http://${MAILCOW_IP}" > /etc/hydrahive2/extensions/mailcow.url

cat > /etc/hydrahive2/extensions/mailcow.credentials.json << CREDFILE
{
  "id": "mailcow",
  "name": "Mailcow (Mail-Server)",
  "fields": [
    {"label": "URL",            "value": "http://${MAILCOW_IP}", "secret": false},
    {"label": "Admin-Login",    "value": "admin",                "secret": false},
    {"label": "Admin-Passwort", "value": "moohoo",               "secret": true},
    {"label": "Hostname",       "value": "${MAILCOW_HOSTNAME}",  "secret": false},
    {"label": "DB-Passwort",    "value": "${MAILCOW_DBPASS}",    "secret": true}
  ]
}
CREDFILE
chown root:hydrahive /etc/hydrahive2/extensions/mailcow.credentials.json
chmod 640 /etc/hydrahive2/extensions/mailcow.credentials.json

success "Mailcow installiert"
info "  UI:          http://${MAILCOW_IP}"
info "  Admin-Login: admin / moohoo"
info "  Passwort SOFORT nach Login ändern!"
info "  Fetchmail:   Mail-Setup → Fetchmail"
info "  Domains:     Mail-Setup → Domains"
