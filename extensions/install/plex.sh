#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

PLEX_REPO_FILE="/etc/apt/sources.list.d/plexmediaserver.list"
PLEX_GPG_FILE="/etc/apt/trusted.gpg.d/plexmediaserver.asc"
PLEX_PORT="32400"

info "Installiere Plex Media Server..."

# --- GPG-Schlüssel ---
if [ ! -f "${PLEX_GPG_FILE}" ]; then
    info "Füge Plex GPG-Schlüssel hinzu..."
    curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x97203C7B3ADCA79D" \
        | gpg --batch --yes --dearmor -o "${PLEX_GPG_FILE}" 2>/dev/null \
        || die "Plex GPG-Schlüssel konnte nicht importiert werden"
    chmod 644 "${PLEX_GPG_FILE}"
    success "GPG-Schlüssel importiert"
fi

# --- Apt-Repository ---
info "Konfiguriere Plex apt-Repository..."
echo "deb [signed-by=${PLEX_GPG_FILE}] https://downloads.plex.tv/repo/deb public main" \
    > "${PLEX_REPO_FILE}"
success "Plex-Repository eingetragen"

# --- Installieren / Aktualisieren ---
info "Aktualisiere Paketliste und installiere plexmediaserver..."
apt-get update -qq
apt-get install -y --quiet plexmediaserver \
    2>/dev/null | grep -E "^(Get|Entpacken|Einrichten|plexmediaserver)" || true
success "plexmediaserver installiert: $(dpkg-query -W -f='${Version}' plexmediaserver 2>/dev/null || echo 'unbekannt')"

# --- Daten-Verzeichnis ---
mkdir -p /var/lib/plexmediaserver/Library
chown -R plex:plex /var/lib/plexmediaserver 2>/dev/null || true

# --- Service ---
systemctl daemon-reload
systemctl enable plexmediaserver
systemctl restart plexmediaserver
success "Service 'plexmediaserver' gestartet"

# --- Warten ---
info "Warte auf Plex (bis 30 s)..."
for i in $(seq 1 15); do
    sleep 2
    curl -sf "http://127.0.0.1:${PLEX_PORT}/web" &>/dev/null && break || true
done
curl -sf "http://127.0.0.1:${PLEX_PORT}/web" &>/dev/null \
    && success "Plex erreichbar" \
    || warn "Plex noch nicht erreichbar — prüfe: systemctl status plexmediaserver"

SERVER_IP=$(hostname -I | awk '{print $1}')

success "Plex Media Server installiert"
info "  URL:    http://${SERVER_IP}:${PLEX_PORT}/web"
info "  Daten:  /var/lib/plexmediaserver"
info "  Beim ersten Aufruf im Browser Setup-Wizard durchlaufen"
