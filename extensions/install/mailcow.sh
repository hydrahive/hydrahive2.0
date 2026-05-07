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

# ── Umgebungs-Prüfung: Docker-Sysctl-Fähigkeit ──────────────────────────────
# Docker schreibt net.ipv4.ip_unprivileged_port_start in jeden Container-Namespace.
# In LXC-Containern (Proxmox etc.) ist das ohne Host-Konfiguration geblockt.
info "Prüfe Docker-Sysctl-Kompatibilität..."
SYSCTL_ERR=$(docker run --rm --sysctl net.ipv4.ip_unprivileged_port_start=0 \
    alpine:latest true 2>&1 || true)
if echo "${SYSCTL_ERR}" | grep -q "ip_unprivileged_port_start"; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║  FEHLER: LXC-Umgebung blockiert Docker-Sysctls                 ║"
    echo "╠══════════════════════════════════════════════════════════════════╣"
    echo "║  Mailcow kann in dieser Umgebung nicht starten.                 ║"
    echo "║                                                                  ║"
    echo "║  Fix auf dem Proxmox-HOST (nicht in diesem Container):          ║"
    echo "║                                                                  ║"
    echo "║  1. LXC-Container-ID herausfinden:  pct list                   ║"
    echo "║  2. In Konfigurationsdatei eintragen:                           ║"
    echo "║     echo 'lxc.sysctl.net.ipv4.ip_unprivileged_port_start = 0'  ║"
    echo "║          >> /etc/pve/lxc/<CTID>.conf                            ║"
    echo "║  3. Container neu starten:  pct reboot <CTID>                   ║"
    echo "║                                                                  ║"
    echo "║  Alternativ: Mailcow auf einem dedizierten Host installieren.   ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    exit 1
fi
success "Docker-Sysctl-Kompatibilität OK"

# ── Netzwerk automatisch erkennen ────────────────────────────────────────────
IFACE=$(ip route | awk '/^default/ {print $5; exit}')
GATEWAY=$(ip route | awk '/^default/ {print $3; exit}')
HOST_IP=$(ip -o -f inet addr show "${IFACE}" | awk 'NR==1{split($4,a,"/"); print a[1]}')
IFS='.' read -r _o1 _o2 _o3 _o4 <<< "${HOST_IP}"
info "Netzwerk: Interface=${IFACE}, Host-IP=${HOST_IP}, Gateway=${GATEWAY}"

# Freie IP im Bereich .200–.250 suchen (nur ARP, kein ping)
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
# Mailcow bindet seine Ports exklusiv an diese IP — kein Konflikt mit HydraHive.
# Sofort aktivieren:
ip addr add "${MAILCOW_IP}/24" dev "${IFACE}" 2>/dev/null || true

# Persistent via systemd (funktioniert unabhängig von netplan/ifupdown):
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
success "IP-Alias ${MAILCOW_IP} gesetzt und persistent eingetragen"

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

# HTTP_BIND/HTTPS_BIND auf Mailcow-IP setzen — nginx bindet nur an diese IP,
# kein Konflikt mit HydraHive auf der Haupt-IP.
if grep -q "^HTTP_BIND=" "${MAILCOW_CONF}"; then
    sed -i "s/^HTTP_BIND=.*/HTTP_BIND=${MAILCOW_IP}/" "${MAILCOW_CONF}"
else
    echo "HTTP_BIND=${MAILCOW_IP}" >> "${MAILCOW_CONF}"
fi
if grep -q "^HTTPS_BIND=" "${MAILCOW_CONF}"; then
    sed -i "s/^HTTPS_BIND=.*/HTTPS_BIND=${MAILCOW_IP}/" "${MAILCOW_CONF}"
else
    echo "HTTPS_BIND=${MAILCOW_IP}" >> "${MAILCOW_CONF}"
fi
success "mailcow.conf: HTTP/HTTPS gebunden an ${MAILCOW_IP}"

# ── Docker-Compose-Override ──────────────────────────────────────────────────
# nginx-mailcow bindet Port 80/443 exklusiv an MAILCOW_IP.
# Alle Services mit sysctls bekommen sysctls:[] (LXC/VM-Kompatibilität).
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
    echo "services:"
    for svc in ${SYSCTL_SERVICES}; do
        printf "  %s:\n    sysctls: []\n" "${svc}"
    done
} > "${MAILCOW_DIR}/docker-compose.override.yml"

success "docker-compose.override.yml: sysctls deaktiviert für: ${SYSCTL_SERVICES}"

# ── Kernel-Sysctl (best-effort, kein Fehler wenn nicht möglich) ──────────────
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
info "Warte auf Mailcow-UI (http://${MAILCOW_IP})..."
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
