#!/usr/bin/env bash
# extensions/install/tuwunel.sh — tuwunel Matrix-Homeserver
# tuwunel ist der offizielle Nachfolger von conduwuit (matrix-construct/tuwunel).
# Das Config-Format (conduwuit.toml, [global]-Schema) und CONDUWUIT_*-Env-Vars bleiben kompatibel.
# Wir verwenden das rohe .zst-Binary (x86_64-v1, Baseline-CPU) für volle Kontrolle über
# Service-Name, Config-Pfad und Federation-Flag.
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
error()   { echo "[FEHLER] $*" >&2; exit 1; }

TUWUNEL_USER="tuwunel"
TUWUNEL_DIR="/var/lib/tuwunel"
TUWUNEL_CONFIG_DIR="/etc/tuwunel"
TUWUNEL_CONFIG="${TUWUNEL_CONFIG_DIR}/tuwunel.toml"
TUWUNEL_BIN="/usr/local/bin/tuwunel"
HH_MATRIX_DIR="${HH_CONFIG_DIR:-/etc/hydrahive}/matrix"

info "Installiere tuwunel Matrix-Homeserver..."

# ── Idempotenz: Binary schon vorhanden? ─────────────────────────────────────
SKIP_DOWNLOAD=0
if [ -f "$TUWUNEL_BIN" ]; then
  INSTALLED_VER=$("$TUWUNEL_BIN" --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "")
  info "tuwunel ${INSTALLED_VER:-?} bereits installiert — prüfe auf Update..."
fi

# ── Aktuelles Release via GitHub API ────────────────────────────────────────
info "Ermittle aktuelles tuwunel Release..."
RELEASE_INFO=$(curl -sfL "https://api.github.com/repos/matrix-construct/tuwunel/releases/latest" || echo "{}")
RELEASE_TAG=$(echo "$RELEASE_INFO" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tag_name',''))")

if [ -z "$RELEASE_TAG" ]; then
  error "tuwunel Release konnte nicht ermittelt werden (GitHub API nicht erreichbar?)."
fi
info "Gefunden: tuwunel $RELEASE_TAG"

# ── Version-Check: Download überspringen wenn gleiche Version läuft ──────────
if [ -f "$TUWUNEL_BIN" ] && [ -n "${INSTALLED_VER:-}" ]; then
  if echo "$RELEASE_TAG" | grep -qF "$INSTALLED_VER"; then
    success "tuwunel $INSTALLED_VER bereits aktuell — Download übersprungen"
    SKIP_DOWNLOAD=1
  fi
fi

if [ "$SKIP_DOWNLOAD" -eq 0 ]; then
  # ── Asset-URL für *-release-all-x86_64-v1-linux-gnu-tuwunel.zst ─────────
  # Exaktes Muster: endet auf "-release-all-x86_64-v1-linux-gnu-tuwunel.zst"
  # NICHT: .tar.zst, -debuginfo, -docker, -oci, -v2, -v3
  ZST_URL=$(echo "$RELEASE_INFO" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for a in d.get('assets', []):
    name = a['name']
    if (name.endswith('-release-all-x86_64-v1-linux-gnu-tuwunel.zst')
            and not name.endswith('.tar.zst')
            and 'debug' not in name
            and 'docker' not in name
            and 'oci' not in name):
        print(a['browser_download_url'])
        break
")

  if [ -z "$ZST_URL" ]; then
    error "Kein passendes tuwunel Asset gefunden (*-release-all-x86_64-v1-linux-gnu-tuwunel.zst) in Release $RELEASE_TAG."
  fi
  info "Asset-URL: $ZST_URL"

  # ── zstd sicherstellen ──────────────────────────────────────────────────
  if ! command -v zstd &>/dev/null; then
    info "zstd nicht gefunden — installiere via apt-get..."
    apt-get install -y zstd
    success "zstd installiert"
  fi

  # ── Binary herunterladen und dekomprimieren ─────────────────────────────
  TMPFILE=$(mktemp /tmp/tuwunel-XXXXXX.zst)
  trap 'rm -f "$TMPFILE"' EXIT

  info "Lade tuwunel $RELEASE_TAG..."
  curl -sL --fail "$ZST_URL" -o "$TMPFILE"

  info "Dekomprimiere Binary..."
  zstd -d "$TMPFILE" -o "${TUWUNEL_BIN}.tmp" --force
  chmod +x "${TUWUNEL_BIN}.tmp"
  mv "${TUWUNEL_BIN}.tmp" "$TUWUNEL_BIN"

  success "tuwunel $RELEASE_TAG installiert nach $TUWUNEL_BIN"
fi # SKIP_DOWNLOAD

# ── System-User anlegen (idempotent) ────────────────────────────────────────
if ! id "$TUWUNEL_USER" &>/dev/null; then
  useradd -r -s /bin/false -d "$TUWUNEL_DIR" "$TUWUNEL_USER"
  success "System-User '$TUWUNEL_USER' angelegt"
else
  info "System-User '$TUWUNEL_USER' bereits vorhanden"
fi

# ── Verzeichnisse anlegen ────────────────────────────────────────────────────
mkdir -p "$TUWUNEL_DIR" "$TUWUNEL_CONFIG_DIR"
chown -R "$TUWUNEL_USER:$TUWUNEL_USER" "$TUWUNEL_DIR"

# ── Hostname ermitteln ───────────────────────────────────────────────────────
SERVER_NAME=$(hostname -f 2>/dev/null || hostname)

# ── Registration-Token: vorhandenen behalten (Idempotenz) ───────────────────
# Neu generieren nur wenn kein gültiger Token existiert (kein Re-Install soll bestehende
# Matrix-Accounts aussperren).
HH_TOKEN_FILE="${HH_MATRIX_DIR}/registration_token"
if [ -f "$HH_TOKEN_FILE" ] && [ -s "$HH_TOKEN_FILE" ]; then
  REG_TOKEN=$(cat "$HH_TOKEN_FILE")
  info "Vorhandenen Registration-Token aus $HH_TOKEN_FILE übernommen"
elif [ -f "$TUWUNEL_CONFIG" ]; then
  # Fallback: Token aus bestehender TOML lesen
  EXISTING_TOKEN=$(grep '^registration_token' "$TUWUNEL_CONFIG" 2>/dev/null \
    | grep -oP '"\K[^"]+' || echo "")
  # Placeholder-Werte ignorieren
  if echo "$EXISTING_TOKEN" | grep -qiE "change|example|placeholder|your|^$"; then
    REG_TOKEN=$(openssl rand -hex 32)
    info "Placeholder-Token in bestehender Config ersetzt"
  else
    REG_TOKEN="$EXISTING_TOKEN"
    info "Bestehenden Token aus TOML übernommen"
  fi
else
  REG_TOKEN=$(openssl rand -hex 32)
  info "Neuen Registration-Token generiert"
fi

# ── Config schreiben ─────────────────────────────────────────────────────────
# conduwuit.toml-Format mit [global]-Schema — tuwunel liest dasselbe Schema.
cat > "$TUWUNEL_CONFIG" << TOML
[global]
server_name = "${SERVER_NAME}"
database_path = "${TUWUNEL_DIR}/rocksdb"
port = 6167
address = "127.0.0.1"

allow_registration = true
registration_token = "${REG_TOKEN}"

# Federation absichtlich deaktiviert — HydraHive Team-Chat ist ein privates Netz.
# Zum Aktivieren: allow_federation = true + öffentlichen Port/DNS einrichten.
allow_federation = false

log = "warn,tuwunel=info"
TOML

chown "$TUWUNEL_USER:$TUWUNEL_USER" "$TUWUNEL_CONFIG"
chmod 640 "$TUWUNEL_CONFIG"
success "tuwunel Konfiguration geschrieben (server_name: $SERVER_NAME)"

# ── HH2-Config-Dir: server_name + registration_token schreiben ──────────────
# HydraHive Backend liest diese Dateien um Matrix-API-Calls zu authentifizieren.
# registration_token wird nur geschrieben wenn noch NICHT vorhanden (s.o. Idempotenz).
mkdir -p "$HH_MATRIX_DIR"
echo -n "$SERVER_NAME" > "${HH_MATRIX_DIR}/server_name"
chmod 644 "${HH_MATRIX_DIR}/server_name"
success "server_name in $HH_MATRIX_DIR/server_name geschrieben"

if [ ! -f "$HH_TOKEN_FILE" ] || [ ! -s "$HH_TOKEN_FILE" ]; then
  echo -n "$REG_TOKEN" > "$HH_TOKEN_FILE"
  chmod 600 "$HH_TOKEN_FILE"
  success "registration_token in $HH_TOKEN_FILE geschrieben"
else
  info "registration_token-Datei bereits vorhanden — nicht überschrieben"
fi
info "Registration-Token: $REG_TOKEN"

# ── Systemd-Unit schreiben ───────────────────────────────────────────────────
cat > /etc/systemd/system/hydrahive-tuwunel.service << UNIT
[Unit]
Description=HydraHive tuwunel Matrix-Homeserver
After=network.target
Documentation=https://github.com/matrix-construct/tuwunel

[Service]
Type=simple
User=${TUWUNEL_USER}
Group=${TUWUNEL_USER}
ExecStart=${TUWUNEL_BIN} --config ${TUWUNEL_CONFIG}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hydrahive-tuwunel

# Härtung
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=${TUWUNEL_DIR}

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable hydrahive-tuwunel
success "systemd-Unit hydrahive-tuwunel aktiviert"

# ── Service starten oder neu starten ────────────────────────────────────────
if systemctl is-active --quiet hydrahive-tuwunel; then
  systemctl restart hydrahive-tuwunel
  success "tuwunel neugestartet"
else
  systemctl start hydrahive-tuwunel
  success "tuwunel gestartet"
fi

# ── Health-Check — Retry-Loop (6x mit 5s Pause) ─────────────────────────────
HEALTH_OK=0
for i in 1 2 3 4 5 6; do
  sleep 5
  if curl -sf "http://127.0.0.1:6167/_matrix/client/versions" &>/dev/null; then
    success "tuwunel antwortet auf http://127.0.0.1:6167/_matrix/client/versions"
    HEALTH_OK=1
    break
  fi
  info "Warte auf tuwunel... ($i/6)"
done

if [ "$HEALTH_OK" -eq 0 ]; then
  warn "tuwunel antwortet nicht — pruefe: journalctl -u hydrahive-tuwunel -n 30"
fi
