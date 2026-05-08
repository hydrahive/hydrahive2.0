#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

PIHOLE_PASSWORD="${PIHOLE_PASSWORD:-}"
[ -n "${PIHOLE_PASSWORD}" ] || die "PIHOLE_PASSWORD nicht gesetzt"

PIHOLE_PORT="8053"
SERVER_IP="$(hostname -I | awk '{print $1}')"

info "Installiere Pi-hole..."

# --- Abhängigkeiten ---
apt-get update -qq
apt-get install -y --quiet curl git python3 \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true

# --- Port 53 freimachen (systemd-resolved blockiert DNS) ---
if systemctl is-active --quiet systemd-resolved 2>/dev/null; then
    info "Deaktiviere systemd-resolved (belegt Port 53)..."
    systemctl stop systemd-resolved
    systemctl disable systemd-resolved
    rm -f /etc/resolv.conf
    echo "nameserver 9.9.9.9" > /etc/resolv.conf
    echo "nameserver 1.1.1.1" >> /etc/resolv.conf
    success "systemd-resolved deaktiviert"
fi

# --- Pi-hole unattended installieren ---
info "Lade Pi-hole Installer..."
mkdir -p /etc/pihole

# WEBPASSWORD: doppelt sha256 wie Pi-hole es erwartet
PIHOLE_HASH="$(printf '%s' "${PIHOLE_PASSWORD}" | sha256sum | awk '{print $1}')"
PIHOLE_HASH2="$(printf '%s' "${PIHOLE_HASH}" | sha256sum | awk '{print $1}')"

cat > /etc/pihole/setupVars.conf << SETUPEOF
PIHOLE_INTERFACE=
IPV4_ADDRESS=${SERVER_IP}/24
IPV6_ADDRESS=
QUERY_LOGGING=true
INSTALL_WEB_SERVER=true
INSTALL_WEB_INTERFACE=true
LIGHTTPD_ENABLED=true
CACHE_SIZE=10000
DNS_FQDN_REQUIRED=false
DNS_BOGUS_PRIV=true
DNSMASQ_LISTENING=local
WEBPASSWORD=${PIHOLE_HASH2}
BLOCKING_ENABLED=true
PIHOLE_DNS_1=9.9.9.9
PIHOLE_DNS_2=1.1.1.1
PIHOLE_DNS_3=
PIHOLE_DNS_4=
DNSSEC=false
REV_SERVER=false
SETUPEOF

curl -fsSL https://install.pi-hole.net -o /tmp/pihole-install.sh \
    || die "Pi-hole Installer konnte nicht heruntergeladen werden"
bash /tmp/pihole-install.sh --unattended 2>&1 | grep -E "^\[|✓|✗|Error" || true
rm -f /tmp/pihole-install.sh
success "Pi-hole installiert"

# --- Passwort nochmals explizit setzen ---
pihole -a -p "${PIHOLE_PASSWORD}" 2>/dev/null \
    || warn "Passwort konnte nicht gesetzt werden — manuell: pihole -a -p PASSWORT"
success "Admin-Passwort gesetzt"

# --- lighttpd auf eigenen Port ---
LIGHTTPD_CONF="/etc/lighttpd/lighttpd.conf"
if [ -f "${LIGHTTPD_CONF}" ]; then
    sed -i "s/^server\.port\s*=.*/server.port = ${PIHOLE_PORT}/" "${LIGHTTPD_CONF}"
    systemctl restart lighttpd 2>/dev/null || true
    success "lighttpd auf Port ${PIHOLE_PORT} umgestellt"
fi

systemctl enable pihole-FTL 2>/dev/null || true
systemctl restart pihole-FTL 2>/dev/null || true

# --- Warten ---
info "Warte auf Pi-hole Web-UI (bis 20 s)..."
for i in $(seq 1 10); do
    sleep 2
    curl -sf "http://127.0.0.1:${PIHOLE_PORT}/admin/" &>/dev/null && break || true
done
curl -sf "http://127.0.0.1:${PIHOLE_PORT}/admin/" &>/dev/null \
    && success "Pi-hole Web-UI erreichbar" \
    || warn "Web-UI noch nicht erreichbar — prüfe: systemctl status lighttpd"

# --- Credentials ---
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/pihole.credentials.json << CREDEOF
{
  "id": "pihole",
  "name": "Pi-hole (DNS-Blocker)",
  "fields": [
    {"label": "URL",      "value": "http://${SERVER_IP}:${PIHOLE_PORT}/admin/", "secret": false},
    {"label": "Passwort", "value": "${PIHOLE_PASSWORD}",                         "secret": true}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/pihole.credentials.json
chmod 640 /etc/hydrahive2/extensions/pihole.credentials.json

success "Pi-hole installiert"
info "  URL:  http://${SERVER_IP}:${PIHOLE_PORT}/admin/"
info "  DNS:  Router-DNS auf ${SERVER_IP} zeigen lassen"
warn "  systemd-resolved wurde deaktiviert — DNS läuft jetzt über Pi-hole"
