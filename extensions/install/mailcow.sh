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
# Mailcow lauscht intern nur auf localhost — nginx proxied von Alias-IP dahin
MAILCOW_HTTP_PORT=8080
MAILCOW_HTTPS_PORT=8443

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
fi

# ── Umgebungs-Prüfung: Docker-Sysctl-Fähigkeit ──────────────────────────────
info "Prüfe Docker-Sysctl-Kompatibilität..."
SYSCTL_ERR=$(docker run --rm --sysctl net.ipv4.ip_unprivileged_port_start=0 \
    alpine:latest true 2>&1 || true)
if echo "${SYSCTL_ERR}" | grep -q "ip_unprivileged_port_start"; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  FEHLER: LXC-Umgebung blockiert Docker-Sysctls                  ║"
    echo "╠══════════════════════════════════════════════════════════════════╣"
    echo "║  Fix auf dem Proxmox-HOST:                                       ║"
    echo "║  echo 'lxc.sysctl.net.ipv4.ip_unprivileged_port_start = 0'      ║"
    echo "║       >> /etc/pve/lxc/<CTID>.conf  &&  pct reboot <CTID>        ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    exit 1
fi
success "Docker-Sysctl-Kompatibilität OK"

# ── Netzwerk automatisch erkennen ────────────────────────────────────────────
IFACE=$(ip route | awk '/^default/ {print $5; exit}')
HOST_IP=$(ip -o -f inet addr show "${IFACE}" | awk 'NR==1{split($4,a,"/"); print a[1]}')
IFS='.' read -r _o1 _o2 _o3 _o4 <<< "${HOST_IP}"
info "Netzwerk: Interface=${IFACE}, Host-IP=${HOST_IP}"

# Freie IP im Bereich .200–.250 (nur ARP-Tabelle prüfen)
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
[ -z "${MAILCOW_IP}" ] && die "Keine freie IP im Bereich ${_o1}.${_o2}.${_o3}.200-250"
info "Mailcow-IP (Alias): ${MAILCOW_IP}"

# ── IP-Alias anlegen ─────────────────────────────────────────────────────────
ip addr add "${MAILCOW_IP}/24" dev "${IFACE}" 2>/dev/null || true

cat > /etc/systemd/system/mailcow-ip.service << UNIT
[Unit]
Description=Mailcow IP-Alias (${MAILCOW_IP} on ${IFACE})
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/ip addr add ${MAILCOW_IP}/24 dev ${IFACE}
ExecStop=/sbin/ip addr del ${MAILCOW_IP}/24 dev ${IFACE}
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable mailcow-ip.service 2>/dev/null || true
success "IP-Alias ${MAILCOW_IP} gesetzt"

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
if [ ! -f "${MAILCOW_CONF}" ]; then
    info "Generiere mailcow.conf..."
    cd "${MAILCOW_DIR}"
    MAILCOW_HOSTNAME="${MAILCOW_HOSTNAME}" MAILCOW_TZ="${MAILCOW_TZ}" bash generate_config.sh
    sed -i "s/^DBPASS=.*/DBPASS=${MAILCOW_DBPASS}/" "${MAILCOW_CONF}"
fi

# Mailcow nur auf localhost lauschen lassen — nginx proxied von Alias-IP dahin.
# Das ist der Standard-Reverse-Proxy-Ansatz für Mailcow.
_set_conf() {
    local key="$1" val="$2"
    if grep -q "^${key}=" "${MAILCOW_CONF}"; then
        sed -i "s|^${key}=.*|${key}=${val}|" "${MAILCOW_CONF}"
    else
        echo "${key}=${val}" >> "${MAILCOW_CONF}"
    fi
}
_set_conf HTTP_BIND  "127.0.0.1"
_set_conf HTTP_PORT  "${MAILCOW_HTTP_PORT}"
_set_conf HTTPS_BIND "127.0.0.1"
_set_conf HTTPS_PORT "${MAILCOW_HTTPS_PORT}"
success "mailcow.conf: nginx auf 127.0.0.1:${MAILCOW_HTTP_PORT}/${MAILCOW_HTTPS_PORT}"

# ── Docker-Compose-Override: sysctls deaktivieren ────────────────────────────
SYSCTL_SERVICES=$(python3 - "${MAILCOW_DIR}/docker-compose.yml" 2>/dev/null <<'PYEOF' \
  || echo "netfilter-mailcow watchdog-mailcow"
import yaml, sys
with open(sys.argv[1]) as f:
    c = yaml.safe_load(f)
svcs = [n for n, s in (c.get("services") or {}).items() if s and s.get("sysctls")]
print(" ".join(svcs))
PYEOF
)
{
    echo "services:"
    for svc in ${SYSCTL_SERVICES}; do
        printf "  %s:\n    sysctls: []\n" "${svc}"
    done
} > "${MAILCOW_DIR}/docker-compose.override.yml"
success "docker-compose.override.yml: sysctls:[] für: ${SYSCTL_SERVICES}"

# ── nginx-Proxy-Konfiguration für Mailcow ────────────────────────────────────
# Neue Site-Datei — kein Eingriff in die bestehende HydraHive-nginx-Config.
TLS_DIR=/etc/hydrahive2/tls
MAILCOW_NGINX_CONF=/etc/nginx/sites-available/mailcow

cat > "${MAILCOW_NGINX_CONF}" << NGINXCONF
# Mailcow Reverse Proxy — generiert von HydraHive Extension-Installer
# HTTP → HTTPS redirect auf Mailcow-IP
server {
    listen ${MAILCOW_IP}:80;
    server_name _;
    return 301 https://\$host\$request_uri;
}

# HTTPS → Mailcow intern (127.0.0.1:${MAILCOW_HTTPS_PORT})
server {
    listen ${MAILCOW_IP}:443 ssl;
    server_name _;

    ssl_certificate     ${TLS_DIR}/hydrahive.crt;
    ssl_certificate_key ${TLS_DIR}/hydrahive.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    location / {
        proxy_pass          https://127.0.0.1:${MAILCOW_HTTPS_PORT};
        proxy_ssl_verify    off;
        proxy_set_header    Host \$host;
        proxy_set_header    X-Real-IP \$remote_addr;
        proxy_set_header    X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto https;
        proxy_http_version  1.1;
        proxy_set_header    Upgrade \$http_upgrade;
        proxy_set_header    Connection "upgrade";
        proxy_read_timeout  86400s;
        client_max_body_size 256M;
    }
}
NGINXCONF

ln -sf "${MAILCOW_NGINX_CONF}" /etc/nginx/sites-enabled/mailcow
nginx -t && systemctl reload nginx
success "nginx-Proxy: ${MAILCOW_IP}:80/443 → 127.0.0.1:${MAILCOW_HTTP_PORT}/${MAILCOW_HTTPS_PORT}"

# ── Kernel-Sysctl (best-effort) ───────────────────────────────────────────────
if sysctl -w net.ipv4.ip_unprivileged_port_start=0 &>/dev/null 2>&1; then
    grep -q "ip_unprivileged_port_start" /etc/sysctl.conf || \
        echo "net.ipv4.ip_unprivileged_port_start=0" >> /etc/sysctl.conf
fi

# ── Starten ──────────────────────────────────────────────────────────────────
info "Starte Mailcow-Stack..."
cd "${MAILCOW_DIR}"
docker compose pull --quiet
docker compose up -d
success "Mailcow-Stack gestartet"

# ── Warten bis UI erreichbar ─────────────────────────────────────────────────
info "Warte auf Mailcow-UI..."
for i in $(seq 1 30); do
    if curl -sf -k --max-time 5 "https://${MAILCOW_IP}/" &>/dev/null; then
        success "Mailcow erreichbar auf https://${MAILCOW_IP}"
        break
    fi
    echo -n "."
    sleep 10
done

# ── URL + Credentials speichern ───────────────────────────────────────────────
mkdir -p /etc/hydrahive2/extensions
echo "https://${MAILCOW_IP}" > /etc/hydrahive2/extensions/mailcow.url

cat > /etc/hydrahive2/extensions/mailcow.credentials.json << CREDFILE
{
  "id": "mailcow",
  "name": "Mailcow (Mail-Server)",
  "fields": [
    {"label": "URL",            "value": "https://${MAILCOW_IP}", "secret": false},
    {"label": "Admin-Login",    "value": "admin",                 "secret": false},
    {"label": "Admin-Passwort", "value": "moohoo",                "secret": true},
    {"label": "Hostname",       "value": "${MAILCOW_HOSTNAME}",   "secret": false},
    {"label": "DB-Passwort",    "value": "${MAILCOW_DBPASS}",     "secret": true}
  ]
}
CREDFILE
chown root:hydrahive /etc/hydrahive2/extensions/mailcow.credentials.json
chmod 640 /etc/hydrahive2/extensions/mailcow.credentials.json

success "Mailcow installiert"
info "  UI:          https://${MAILCOW_IP}"
info "  Admin-Login: admin / moohoo"
info "  Passwort SOFORT nach Login ändern!"
