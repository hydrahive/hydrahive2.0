#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

AGH_DIR="/opt/adguard-home"
AGH_BINARY="${AGH_DIR}/AdGuardHome"
AGH_YAML="${AGH_DIR}/AdGuardHome.yaml"
AGH_DATA_DIR="/var/lib/adguard-home"
AGH_USER="adguardhome"
WEB_PORT="8300"

ADGUARD_DNS_IP="${ADGUARD_DNS_IP:-}"
if [ -n "${ADGUARD_DNS_IP}" ]; then
    DNS_BIND="${ADGUARD_DNS_IP}"
    DNS_PORT="53"
else
    DNS_BIND="0.0.0.0"
    DNS_PORT="3053"
fi

info "Installiere AdGuard Home — DNS-Port: ${DNS_PORT}, Web-UI: ${WEB_PORT}"

# --- Neueste Version ermitteln ---
RELEASE_JSON="$(curl -sf "https://api.github.com/repos/AdguardTeam/AdGuardHome/releases/latest")"
LATEST_TAG="$(printf '%s' "${RELEASE_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tag_name','v0.107.54'))" 2>/dev/null || echo "v0.107.54")"
info "Neueste Version: ${LATEST_TAG}"

# --- Schon installiert und aktuell? ---
if [ -x "${AGH_BINARY}" ]; then
    INSTALLED_VERSION="$("${AGH_BINARY}" --version 2>/dev/null | grep -oP 'v[\d.]+' | head -1 || echo "")"
    if [ "${INSTALLED_VERSION}" = "${LATEST_TAG}" ] && [ -f "${AGH_YAML}" ]; then
        success "AdGuard Home ${INSTALLED_VERSION} bereits aktuell"
        systemctl start adguardhome 2>/dev/null || true
        exit 0
    fi
    info "Update von ${INSTALLED_VERSION} auf ${LATEST_TAG}..."
    systemctl stop adguardhome 2>/dev/null || true
fi

# --- Abhängigkeiten ---
apt-get install -y --quiet curl wget python3 2>/dev/null | grep -E "^(Get|Entpacken|Einrichten)" || true
command -v sha256sum &>/dev/null || apt-get install -y --quiet coreutils

# --- Download ---
ARCH="amd64"
PLATFORM="linux"
TARBALL="AdGuardHome_${PLATFORM}_${ARCH}.tar.gz"
CHECKSUMS_FILE="AdGuardHome_checksums.txt"
BASE_URL="https://github.com/AdguardTeam/AdGuardHome/releases/download/${LATEST_TAG}"

info "Lade ${TARBALL} herunter..."
curl -fSL "${BASE_URL}/${TARBALL}" -o "/tmp/${TARBALL}" \
    || die "Download fehlgeschlagen"

# SHA256-Verifizierung
if curl -fsSL "${BASE_URL}/${CHECKSUMS_FILE}" -o "/tmp/${CHECKSUMS_FILE}" 2>/dev/null; then
    EXPECTED_HASH="$(grep "${TARBALL}" "/tmp/${CHECKSUMS_FILE}" | awk '{print $1}')"
    ACTUAL_HASH="$(sha256sum "/tmp/${TARBALL}" | awk '{print $1}')"
    if [ -n "${EXPECTED_HASH}" ] && [ "${EXPECTED_HASH}" != "${ACTUAL_HASH}" ]; then
        rm -f "/tmp/${TARBALL}" "/tmp/${CHECKSUMS_FILE}"
        die "SHA256-Prüfsumme stimmt nicht überein"
    fi
    success "SHA256 korrekt: ${ACTUAL_HASH:0:16}..."
    rm -f "/tmp/${CHECKSUMS_FILE}"
else
    warn "Checksum-Datei nicht verfügbar — überspringe Verifikation"
fi

# --- Entpacken ---
mkdir -p "${AGH_DIR}"
tar -xzf "/tmp/${TARBALL}" -C "${AGH_DIR}" --strip-components=1
rm -f "/tmp/${TARBALL}"
# Doppelte Verschachtelung korrigieren falls nötig
if [ -d "${AGH_BINARY}" ] && [ -f "${AGH_BINARY}/AdGuardHome" ]; then
    mv "${AGH_BINARY}/AdGuardHome" "${AGH_DIR}/AdGuardHome_tmp"
    rm -rf "${AGH_BINARY}"
    mv "${AGH_DIR}/AdGuardHome_tmp" "${AGH_BINARY}"
fi
chmod 750 "${AGH_BINARY}"
success "AdGuardHome ${LATEST_TAG} nach ${AGH_DIR} entpackt"

# --- System-User ---
if ! id "${AGH_USER}" &>/dev/null; then
    if getent group "${AGH_USER}" &>/dev/null; then
        useradd -r -s /bin/false -d "${AGH_DATA_DIR}" -m -g "${AGH_USER}" "${AGH_USER}"
    else
        useradd -r -s /bin/false -d "${AGH_DATA_DIR}" -m "${AGH_USER}"
    fi
    success "System-User '${AGH_USER}' angelegt"
fi

mkdir -p "${AGH_DATA_DIR}"
chown -R "${AGH_USER}:${AGH_USER}" "${AGH_DATA_DIR}" "${AGH_DIR}"

# --- IP-Alias (nur wenn ADGUARD_DNS_IP gesetzt) ---
if [ -n "${ADGUARD_DNS_IP}" ]; then
    info "Richte dedizierte DNS-IP ${ADGUARD_DNS_IP} ein..."
    PRIMARY_IFACE="$(ip route | awk '/^default/ { print $5; exit }')"
    [ -n "${PRIMARY_IFACE}" ] || die "Kein primäres Netzwerk-Interface gefunden"
    IFACE_PREFIX="$(ip -4 addr show dev "${PRIMARY_IFACE}" | awk '/inet / { split($2,a,"/"); print a[2]; exit }')"
    IFACE_PREFIX="${IFACE_PREFIX:-24}"

    cat > /etc/systemd/system/adguard-dns-alias.service << ALIASEOF
[Unit]
Description=AdGuard Home DNS IP Alias (${ADGUARD_DNS_IP})
Before=adguardhome.service
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/sbin/ip addr add ${ADGUARD_DNS_IP}/${IFACE_PREFIX} dev ${PRIMARY_IFACE} 2>/dev/null || true
ExecStop=/sbin/ip addr del ${ADGUARD_DNS_IP}/${IFACE_PREFIX} dev ${PRIMARY_IFACE} 2>/dev/null || true

[Install]
WantedBy=multi-user.target
ALIASEOF
    systemctl daemon-reload
    systemctl enable adguard-dns-alias
    systemctl start adguard-dns-alias
    success "IP-Alias ${ADGUARD_DNS_IP} auf ${PRIMARY_IFACE} aktiv"
fi

# --- Initiale Konfiguration ---
if [ ! -f "${AGH_YAML}" ]; then
    info "Erstelle initiale AdGuardHome.yaml..."
    cat > "${AGH_YAML}" << YAMLEOF
http:
  pprof:
    port: 6060
    enabled: false
  address: 0.0.0.0:${WEB_PORT}
  session_ttl: 720h
users: []
auth_attempts: 5
block_auth_min: 15
http_proxy: ""
language: de
theme: auto
debug_pprof: false
web_session_ttl: 720

dns:
  bind_hosts:
    - ${DNS_BIND}
  port: ${DNS_PORT}
  anonymize_client_ip: false
  ratelimit: 20
  ratelimit_whitelist: []
  refuse_any: true
  upstream_dns:
    - https://dns.cloudflare.com/dns-query
    - https://dns.google/dns-query
  upstream_dns_file: ""
  bootstrap_dns:
    - 9.9.9.10
    - 149.112.112.10
  fallback_dns: []
  all_servers: false
  fastest_addr: false
  fastest_timeout: 1s
  allowed_clients: []
  disallowed_clients: []
  blocked_hosts:
    - version.bind
    - id.server
    - hostname.bind
  trusted_proxies:
    - 127.0.0.0/8
    - ::1/128
  cache_size: 4194304
  cache_ttl_min: 0
  cache_ttl_max: 0
  cache_optimistic: false
  filtering_enabled: true
  filters_update_interval: 24
  parental_enabled: false
  safebrowsing_enabled: false
  safesearch:
    enabled: false
  rewrites: []
  upstream_timeout: 10s
  serve_plain_dns: true

tls:
  enabled: false

querylog:
  interval: 90h
  size_memory: 1000
  enabled: true
  file_enabled: true

statistics:
  interval: 90h
  enabled: true
  limit: 0

filters:
  - enabled: true
    url: https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt
    name: AdGuard DNS filter
    id: 1
  - enabled: true
    url: https://adguardteam.github.io/HostlistsRegistry/assets/filter_2.txt
    name: AdAway Default Blocklist
    id: 2

whitelist_filters: []
user_rules: []

dhcp:
  enabled: false
  interface_name: ""
  local_domain_name: lan

clients:
  runtime_sources:
    whois: true
    arp: true
    rdns: true
    dhcp: true
    hosts: true
  persistent: []

log:
  enabled: true
  file: ""
  max_backups: 0
  max_size: 100
  max_age: 3
  compress: false

schema_version: 28
YAMLEOF
    chown "${AGH_USER}:${AGH_USER}" "${AGH_YAML}"
    chmod 640 "${AGH_YAML}"
    success "Konfiguration erstellt"
fi

# --- systemd Service ---
cat > /etc/systemd/system/adguardhome.service << SVCEOF
[Unit]
Description=AdGuard Home DNS Sinkhole
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${AGH_USER}
Group=${AGH_USER}
WorkingDirectory=${AGH_DIR}
ExecStart=${AGH_BINARY} \
    --config ${AGH_YAML} \
    --work-dir ${AGH_DATA_DIR} \
    --no-check-update \
    --pidfile ""
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable adguardhome
systemctl restart adguardhome
success "AdGuard Home Service gestartet"

# --- Warten auf Start ---
info "Warte auf AdGuard Home (bis 20 s)..."
for i in $(seq 1 10); do
    sleep 2
    if curl -sf "http://127.0.0.1:${WEB_PORT}" &>/dev/null; then
        break
    fi
done
if curl -sf "http://127.0.0.1:${WEB_PORT}" &>/dev/null; then
    success "AdGuard Home Web-UI erreichbar"
else
    warn "Web-UI noch nicht erreichbar — prüfe: journalctl -u adguardhome"
fi

# --- Credentials speichern ---
mkdir -p /etc/hydrahive2/extensions
cat > /etc/hydrahive2/extensions/adguard-home.credentials.json << CREDEOF
{
  "id": "adguard-home",
  "name": "AdGuard Home (DNS-Blocker)",
  "fields": [
    {"label": "URL",       "value": "http://127.0.0.1:${WEB_PORT}", "secret": false},
    {"label": "DNS-Port",  "value": "${DNS_PORT} (${DNS_BIND})",     "secret": false},
    {"label": "Version",   "value": "${LATEST_TAG}",                 "secret": false}
  ]
}
CREDEOF
chown root:hydrahive /etc/hydrahive2/extensions/adguard-home.credentials.json
chmod 640 /etc/hydrahive2/extensions/adguard-home.credentials.json

success "AdGuard Home installiert"
info "  Web-UI:   http://127.0.0.1:${WEB_PORT}"
info "  DNS-Port: ${DNS_PORT} auf ${DNS_BIND}"
if [ -n "${ADGUARD_DNS_IP}" ]; then
    info "  Router-DNS → ${ADGUARD_DNS_IP} (Port 53)"
else
    warn "  Hinweis: Router-DNS auf Server-IP:${DNS_PORT} zeigen lassen"
fi
