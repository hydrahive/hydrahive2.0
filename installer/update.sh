#!/usr/bin/env bash
# HydraHive2 — Update auf den neuesten Stand der main-Branch.
set -euo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_USER="${HH_USER:-hydrahive}"
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/etc/hydrahive2}"

log() { printf "\033[1;36m[hh2-update]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-update]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Bitte mit sudo / als root ausführen."
[ -d "$HH_REPO_DIR/.git" ] || err "$HH_REPO_DIR ist kein Git-Repo."

cd "$HH_REPO_DIR"

# Re-exec-Schutz: nach git pull prüfen wir ob update.sh sich selbst geändert
# hat. Falls ja, exec mit der neuen Version damit neuer Migrations-/Self-Heal-
# Code direkt im AKTUELLEN Lauf greift (nicht erst beim nächsten — siehe #89).
SELF_PATH="$HH_REPO_DIR/installer/update.sh"
SELF_HASH_BEFORE=""
if [ -f "$SELF_PATH" ]; then
  SELF_HASH_BEFORE="$(sha256sum "$SELF_PATH" 2>/dev/null | cut -d' ' -f1 || echo)"
fi

log "SSH-Verzeichnis für $HH_USER prüfen"
HH_HOME="/home/$HH_USER"
SSH_DIR="$HH_HOME/.ssh"
mkdir -p "$SSH_DIR"
chown -R "$HH_USER:$HH_USER" "$HH_HOME"
chmod 700 "$SSH_DIR"
touch "$SSH_DIR/known_hosts"
chown "$HH_USER:$HH_USER" "$SSH_DIR/known_hosts"
chmod 600 "$SSH_DIR/known_hosts"
if ! grep -q "github.com" "$SSH_DIR/known_hosts" 2>/dev/null; then
  ssh-keyscan -t ed25519,rsa github.com 2>/dev/null >> "$SSH_DIR/known_hosts" || true
  chown "$HH_USER:$HH_USER" "$SSH_DIR/known_hosts"
fi

log "git pull"
sudo -u hydrahive git pull --ff-only

# Wenn update.sh selbst durch den Pull verändert wurde: einmalig re-exec mit
# der neuen Version. HH_UPDATE_REEXECED schützt vor Endlos-Loop.
if [ -z "${HH_UPDATE_REEXECED:-}" ] && [ -n "$SELF_HASH_BEFORE" ]; then
  SELF_HASH_AFTER="$(sha256sum "$SELF_PATH" 2>/dev/null | cut -d' ' -f1 || echo)"
  if [ -n "$SELF_HASH_AFTER" ] && [ "$SELF_HASH_BEFORE" != "$SELF_HASH_AFTER" ]; then
    log "update.sh wurde durch git pull aktualisiert — re-exec mit neuer Version"
    HH_UPDATE_REEXECED=1 exec bash "$SELF_PATH" "$@"
  fi
fi

log "Node.js prüfen"
if ! command -v node >/dev/null 2>&1 || [ "$(node -v 2>/dev/null | cut -d. -f1 | tr -d v)" -lt 20 ]; then
  log "Node.js 20 fehlt — installiere via NodeSource"
  export DEBIAN_FRONTEND=noninteractive
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null
  apt-get install -y nodejs >/dev/null
fi

log "Backend-Dependencies aktualisieren"
"$HH_REPO_DIR/.venv/bin/pip" install --quiet -e "$HH_REPO_DIR/core"

log "Frontend neu bauen"
cd "$HH_REPO_DIR/frontend"
sudo -u hydrahive npm install --silent
sudo -u hydrahive npm run build --silent

WA_BRIDGE_DIR="$HH_REPO_DIR/core/src/hydrahive/communication/whatsapp/bridge"
if [ -f "$WA_BRIDGE_DIR/package.json" ]; then
  log "WhatsApp-Bridge: npm install"
  cd "$WA_BRIDGE_DIR"
  npm install --cache /tmp/npm-cache-hh --no-audit --no-fund --silent
  chown -R hydrahive:hydrahive "$WA_BRIDGE_DIR/node_modules"
fi

log "Systemd-Timer-Units prüfen und migrieren"
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"

# Alte Path-Units deaktivieren falls noch vorhanden (Migration inotify → Timer)
for old in hydrahive2-update.path hydrahive2-restart.path; do
  if [ -f "/etc/systemd/system/$old" ]; then
    systemctl stop "$old" >/dev/null 2>&1 || true
    systemctl disable "$old" >/dev/null 2>&1 || true
    rm -f "/etc/systemd/system/$old"
  fi
done

if [ ! -f /etc/systemd/system/hydrahive2-update.timer ] || [ ! -f /etc/systemd/system/hydrahive2-update.service ]; then
  log "Self-Update-Units anlegen"
  cat > /etc/systemd/system/hydrahive2-update.service <<EOF
[Unit]
Description=HydraHive2 Self-Update Runner
ConditionPathExists=$HH_DATA_DIR/.update_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.update_request
ExecStart=$HH_REPO_DIR/installer/update.sh
StandardOutput=append:/var/log/hydrahive2-update.log
StandardError=append:/var/log/hydrahive2-update.log
EOF
  cat > /etc/systemd/system/hydrahive2-update.timer <<EOF
[Unit]
Description=HydraHive2 Update-Trigger Poller

[Timer]
OnBootSec=30s
OnUnitActiveSec=5s
AccuracySec=1s
Unit=hydrahive2-update.service

[Install]
WantedBy=timers.target
EOF
  touch /var/log/hydrahive2-update.log
  chmod 644 /var/log/hydrahive2-update.log
  systemctl daemon-reload
  systemctl enable hydrahive2-update.timer >/dev/null 2>&1
  systemctl restart hydrahive2-update.timer
fi

if [ ! -f /etc/systemd/system/hydrahive2-restart.timer ] || [ ! -f /etc/systemd/system/hydrahive2-restart.service ]; then
  log "Restart-Trigger-Units anlegen"
  cat > /etc/systemd/system/hydrahive2-restart.service <<EOF
[Unit]
Description=HydraHive2 Restart Runner
ConditionPathExists=$HH_DATA_DIR/.restart_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.restart_request
ExecStart=/bin/systemctl restart hydrahive2.service
EOF
  cat > /etc/systemd/system/hydrahive2-restart.timer <<EOF
[Unit]
Description=HydraHive2 Restart-Trigger Poller

[Timer]
OnBootSec=10s
OnUnitActiveSec=5s
AccuracySec=1s
Unit=hydrahive2-restart.service

[Install]
WantedBy=timers.target
EOF
  systemctl daemon-reload
  systemctl enable hydrahive2-restart.timer >/dev/null 2>&1
  systemctl restart hydrahive2-restart.timer
fi

if [ ! -f /etc/systemd/system/hydrahive2-samba.timer ] || [ ! -f /etc/systemd/system/hydrahive2-samba.service ]; then
  log "Samba-Setup-Units anlegen"
  cat > /etc/systemd/system/hydrahive2-samba.service <<EOF
[Unit]
Description=HydraHive2 Samba-Setup Runner
ConditionPathExists=$HH_DATA_DIR/.samba_setup_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.samba_setup_request
Environment=HH_USER=$HH_USER
Environment=HH_DATA_DIR=$HH_DATA_DIR
Environment=HH_CONFIG_DIR=$HH_CONFIG_DIR
ExecStart=$HH_REPO_DIR/installer/modules/47-samba.sh
StandardOutput=append:/var/log/hydrahive2-samba.log
StandardError=append:/var/log/hydrahive2-samba.log
EOF
  cat > /etc/systemd/system/hydrahive2-samba.timer <<EOF
[Unit]
Description=HydraHive2 Samba-Setup Trigger Poller

[Timer]
OnBootSec=60s
OnUnitActiveSec=5s
AccuracySec=1s
Unit=hydrahive2-samba.service

[Install]
WantedBy=timers.target
EOF
  touch /var/log/hydrahive2-samba.log
  chmod 644 /var/log/hydrahive2-samba.log
  systemctl daemon-reload
  systemctl enable hydrahive2-samba.timer >/dev/null 2>&1
  systemctl restart hydrahive2-samba.timer
fi

if [ ! -f /etc/systemd/system/hydrahive2-bridge.timer ] || [ ! -f /etc/systemd/system/hydrahive2-bridge.service ]; then
  log "Bridge-Setup-Units anlegen"
  cat > /etc/systemd/system/hydrahive2-bridge.service <<EOF
[Unit]
Description=HydraHive2 Bridge-Setup Runner
ConditionPathExists=$HH_DATA_DIR/.bridge_setup_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.bridge_setup_request
ExecStart=$HH_REPO_DIR/installer/setup-bridge.sh
StandardOutput=append:/var/log/hydrahive2-bridge.log
StandardError=append:/var/log/hydrahive2-bridge.log
EOF
  cat > /etc/systemd/system/hydrahive2-bridge.timer <<EOF
[Unit]
Description=HydraHive2 Bridge-Setup Trigger Poller

[Timer]
OnBootSec=60s
OnUnitActiveSec=5s
AccuracySec=1s
Unit=hydrahive2-bridge.service

[Install]
WantedBy=timers.target
EOF
  touch /var/log/hydrahive2-bridge.log
  chmod 644 /var/log/hydrahive2-bridge.log
  systemctl daemon-reload
  systemctl enable hydrahive2-bridge.timer >/dev/null 2>&1
  systemctl restart hydrahive2-bridge.timer
fi

if [ ! -f /etc/systemd/system/hydrahive2-voice.timer ] || [ ! -f /etc/systemd/system/hydrahive2-voice.service ]; then
  log "Voice-Install-Units anlegen"
  cat > /etc/systemd/system/hydrahive2-voice.service <<EOF
[Unit]
Description=HydraHive2 Voice-Install Runner
ConditionPathExists=$HH_DATA_DIR/.voice_install_request

[Service]
Type=oneshot
ExecStartPre=/bin/rm -f $HH_DATA_DIR/.voice_install_request
ExecStart=$HH_REPO_DIR/installer/modules/55-voice.sh
StandardOutput=append:/var/log/hydrahive2-voice.log
StandardError=append:/var/log/hydrahive2-voice.log
EOF
  cat > /etc/systemd/system/hydrahive2-voice.timer <<EOF
[Unit]
Description=HydraHive2 Voice-Install Trigger Poller

[Timer]
OnBootSec=60s
OnUnitActiveSec=5s
AccuracySec=1s
Unit=hydrahive2-voice.service

[Install]
WantedBy=timers.target
EOF
  touch /var/log/hydrahive2-voice.log
  chmod 644 /var/log/hydrahive2-voice.log
  systemctl daemon-reload
  systemctl enable hydrahive2-voice.timer >/dev/null 2>&1
  systemctl restart hydrahive2-voice.timer
fi

if ! command -v gh >/dev/null 2>&1; then
  log "gh-CLI fehlt — installiere"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | gpg --dearmor -o /etc/apt/keyrings/githubcli-archive-keyring.gpg
  chmod 644 /etc/apt/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y gh >/dev/null
fi

if ! command -v qemu-system-x86_64 >/dev/null 2>&1 \
   || ! systemctl is-active --quiet hydrahive2-websockify.service; then
  log "VM-Manager-Setup fehlt oder unvollständig — starte 65-vms.sh"
  HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" \
    INSTALLER_DIR="$HH_REPO_DIR/installer" \
    bash "$HH_REPO_DIR/installer/modules/65-vms.sh"
fi

# incus-Setup muss VOR dem Voice-Check laufen — 55-voice.sh nutzt incus
# als STT-Container-Runtime (kein Docker mehr).
if ! command -v incus >/dev/null 2>&1 \
   || ! incus storage list 2>/dev/null | grep -q "default" \
   || [ ! -d "/home/$HH_USER/.config/incus" ]; then
  log "Container-Manager-Setup fehlt — starte 70-containers.sh"
  HH_USER="$HH_USER" \
    bash "$HH_REPO_DIR/installer/modules/70-containers.sh"
fi

# Voice-Setup nach incus — STT läuft jetzt in einem incus-LXC (kein Docker).
# Vier Bedingungen — alle müssen erfüllt sein:
# 1. incus-Container 'hydrahive2-stt' läuft
# 2. proxy-device 'stt-port' am Container existiert (Port-Forward zum Host)
# 3. mmx-CLI (TTS) installiert
# 4. Port 10300 am Host hört (End-to-End-Bestätigung)
voice_ok=1
if ! incus list --format=csv -c n,s 2>/dev/null | grep -qx "hydrahive2-stt,RUNNING"; then
  voice_ok=0
elif ! incus config device show hydrahive2-stt 2>/dev/null | grep -q "^stt-port:"; then
  voice_ok=0
elif ! command -v mmx >/dev/null 2>&1; then
  voice_ok=0
elif ! command -v ffmpeg >/dev/null 2>&1; then
  voice_ok=0
elif ! ss -tln 2>/dev/null | grep -q "127.0.0.1:10300"; then
  voice_ok=0
fi
if [ "$voice_ok" = "0" ]; then
  log "Voice-Setup unvollständig — starte 55-voice.sh"
  # ffmpeg am Host: Voice-Stack braucht das für mp4→pcm und ogg-Konvertierung.
  # Falls 00-deps.sh das nicht installiert hat (alte Installs vor Migration):
  if ! command -v ffmpeg >/dev/null 2>&1; then
    log "ffmpeg fehlt am Host — installieren"
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg >/dev/null 2>&1 || true
  fi
  bash "$HH_REPO_DIR/installer/modules/55-voice.sh"
fi

# mmx-Cache-Verzeichnis muss als hydrahive existieren BEVOR die Service-Unit
# es als ReadWritePaths einträgt — sonst wirft systemd "missing path".
HH_HOME_DIR="/home/$HH_USER"
if id "$HH_USER" >/dev/null 2>&1 && [ ! -d "$HH_HOME_DIR/.mmx" ]; then
  install -d -o "$HH_USER" -g "$HH_USER" -m 0700 "$HH_HOME_DIR/.mmx"
fi

# Service-File auf HOME-Env + ReadWritePaths-Erweiterung migrieren
SERVICE_FILE=/etc/systemd/system/hydrahive2.service
if [ -f "$SERVICE_FILE" ]; then
  NEEDS_REWRITE=0
  grep -q "^Environment=HOME=" "$SERVICE_FILE" || NEEDS_REWRITE=1
  grep -q "ReadWritePaths=.*\.config" "$SERVICE_FILE" || NEEDS_REWRITE=1
  grep -q "ReadWritePaths=.*\.mmx" "$SERVICE_FILE" || NEEDS_REWRITE=1
  # Migration: alte sudo-Workarounds (ExecStartPre /run/sudo, RW=/run/sudo)
  # raus — wir nutzen jetzt tailscale --operator statt sudo
  grep -q "ReadWritePaths=.*/run/sudo" "$SERVICE_FILE" && NEEDS_REWRITE=1
  grep -q "ExecStartPre.*mkdir.*run/sudo" "$SERVICE_FILE" && NEEDS_REWRITE=1
  grep -q "^NoNewPrivileges=true" "$SERVICE_FILE" || NEEDS_REWRITE=1
  if [ "$NEEDS_REWRITE" = "1" ]; then
    log "Service-File braucht Update — neu schreiben"
    HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" HH_CONFIG_DIR="$HH_CONFIG_DIR" \
      HH_HOST="${HH_HOST:-127.0.0.1}" HH_PORT="${HH_PORT:-8001}" \
      HH_REPO_DIR="$HH_REPO_DIR" \
      bash "$HH_REPO_DIR/installer/modules/50-systemd.sh"
  fi
fi

log "nginx-Config prüfen"
NGINX_CONF=/etc/nginx/sites-available/hydrahive2
if ! command -v nginx >/dev/null 2>&1 || [ ! -f "$NGINX_CONF" ]; then
  log "nginx fehlt oder nicht konfiguriert — starte 60-nginx.sh"
  HH_HOST="${HH_HOST:-127.0.0.1}" HH_PORT="${HH_PORT:-8001}" \
    HH_REPO_DIR="$HH_REPO_DIR" \
    bash "$HH_REPO_DIR/installer/modules/60-nginx.sh"
else
  NEEDS_REWRITE=0
  grep -q "ssl_certificate"      "$NGINX_CONF" || NEEDS_REWRITE=1
  grep -q "/vnc-ws/"             "$NGINX_CONF" || NEEDS_REWRITE=1
  grep -q "client_max_body_size 8G" "$NGINX_CONF" || NEEDS_REWRITE=1
  grep -q "connection_upgrade"   "$NGINX_CONF" || NEEDS_REWRITE=1
  if [ "$NEEDS_REWRITE" = "1" ]; then
    log "nginx: Config braucht Update (HTTPS / VNC-Proxy / ISO-Upload-Limit) — neu schreiben"
    HH_HOST="${HH_HOST:-127.0.0.1}"
    HH_PORT="${HH_PORT:-8001}"
    HH_REPO_DIR="$HH_REPO_DIR" HH_HOST="$HH_HOST" HH_PORT="$HH_PORT" \
      bash "$HH_REPO_DIR/installer/modules/60-nginx.sh"
  fi
fi

if [ -x "$HH_REPO_DIR/installer/modules/75-agentlink.sh" ]; then
  log "HydraLink (AgentLink) Update über 75-agentlink.sh"
  # Wrapper rufen statt /opt/hydralink/installer/install.sh direkt — sonst
  # wird HL_BACKEND_PORT=9000 nicht gesetzt und hydralink fällt auf 8000 zurück.
  bash "$HH_REPO_DIR/installer/modules/75-agentlink.sh" || log "hydralink-install failed — weiter"
fi

if [ "${HH_INSTALL_TAILSCALE:-yes}" != "no" ] && [ -x "$HH_REPO_DIR/installer/modules/80-tailscale.sh" ]; then
  log "Tailscale-Setup (installieren falls nicht da, Operator setzen)"
  bash "$HH_REPO_DIR/installer/modules/80-tailscale.sh" || log "tailscale-update failed — weiter"
fi

log "Service neu starten"
systemctl restart hydrahive2.service

sleep 2
if systemctl is-active --quiet hydrahive2.service; then
  log "Update erfolgreich, Service läuft."
else
  log "Service-Neustart fehlgeschlagen — siehe: journalctl -u hydrahive2 -n 50"
  exit 1
fi
