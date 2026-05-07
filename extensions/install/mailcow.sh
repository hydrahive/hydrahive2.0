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

# Wenn IFACE eine Bridge ist: macvlan braucht das physische NIC darunter
if [ -d "/sys/class/net/${IFACE}/brif" ]; then
    MACVLAN_PARENT=$(ls "/sys/class/net/${IFACE}/brif/" | head -1)
    if [ -z "${MACVLAN_PARENT}" ]; then
        die "Bridge ${IFACE} hat keine Member-Interfaces — macvlan nicht möglich"
    fi
    info "Bridge erkannt: ${IFACE} → physisches NIC: ${MACVLAN_PARENT}"
else
    MACVLAN_PARENT="${IFACE}"
fi

HOST_IP=$(ip -o -f inet addr show "${IFACE}" | awk 'NR==1{split($4,a,"/"); print a[1]}')
IFS='.' read -r _o1 _o2 _o3 _o4 <<< "${HOST_IP}"
SUBNET="${_o1}.${_o2}.${_o3}.0/24"
info "Netzwerk: Interface=${IFACE}, macvlan-Parent=${MACVLAN_PARENT}, Gateway=${GATEWAY}, Subnet=${SUBNET}"

# Freie IP im Bereich .200–.250 suchen.
# Nur ARP-Tabelle prüfen — kein ping (ping erzeugt selbst "incomplete" ARP-Einträge
# die dann alle IPs als belegt markieren würden).
USED_IPS=$(arp -n 2>/dev/null | awk '/ether/ {print $1}')
MAILCOW_IP=""
for last in $(seq 200 250); do
    candidate="${_o1}.${_o2}.${_o3}.${last}"
    [ "${candidate}" = "${HOST_IP}" ] && continue
    if ! echo "${USED_IPS}" | grep -qx "${candidate}"; then
        MAILCOW_IP="${candidate}"
        break
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
        --opt parent="${MACVLAN_PARENT}" \
        "${MACVLAN_NET}"
    success "macvlan-Netzwerk ${MACVLAN_NET} erstellt"
else
    info "macvlan-Netzwerk ${MACVLAN_NET} bereits vorhanden"
fi

# ── Docker-Compose-Override ──────────────────────────────────────────────────
# nginx-mailcow bekommt die dedizierte LAN-IP über macvlan.
# Alle Services mit sysctls: bekommen sysctls:[] — Fix für LXC/VM ohne Kernel-Rechte.
# Dynamisch geparst damit künftige Mailcow-Versionen automatisch abgedeckt sind.
SYSCTL_SERVICES=$(python3 - "${MAILCOW_DIR}/docker-compose.yml" 2>/dev/null <<'PYEOF' \
  || echo "netfilter-mailcow watchdog-mailcow"
import yaml, sys
with open(sys.argv[1]) as f:
    c = yaml.safe_load(f)
svcs = [n for n, s in (c.get("services") or {}).items() if s and s.get("sysctls")]
print(" ".join(svcs))
PYEOF
)
info "Services mit sysctls: ${SYSCTL_SERVICES}"

{
    cat << HEADER
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
HEADER
    for svc in ${SYSCTL_SERVICES}; do
        [ "${svc}" = "nginx-mailcow" ] && continue
        printf "  %s:\n    sysctls: []\n" "${svc}"
    done
} > "${MAILCOW_DIR}/docker-compose.override.yml"

success "docker-compose.override.yml erstellt (IP: ${MAILCOW_IP}, sysctls deaktiviert: ${SYSCTL_SERVICES})"

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
