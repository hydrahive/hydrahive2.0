#!/usr/bin/env bash
# Container-Manager Setup: incus + dir-Storage + Default-Profil-Tweaks.
#
# Idempotent: prüft jeden Schritt einzeln.
#
# Nested-LXC-Umgebung erkannt → setzt security.privileged=true UND
# security.nesting=true im default-Profil. Sonst (Bare-Metal) bleibt
# das Profil unprivileged.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }
HH_USER="${HH_USER:-hydrahive}"

log "incus-Paket installieren"
DEBIAN_FRONTEND=noninteractive apt-get install -y incus

# incus admin init mit dir-Storage falls noch nicht initialisiert
if ! incus storage list 2>/dev/null | grep -q "default.*dir"; then
  log "incus initialisieren (dir-Storage, kein Bridge-Auto-Setup)"
  cat <<EOF | incus admin init --preseed 2>&1 | tail -5
config: {}
networks: []
storage_pools:
- config: {}
  description: ""
  name: default
  driver: dir
profiles:
- config: {}
  description: ""
  devices:
    root:
      path: /
      pool: default
      type: disk
  name: default
projects: []
cluster: null
EOF
fi

# images-Remote (offizielles Public-Repo) sicherstellen
if ! incus remote list 2>/dev/null | grep -q "images.*linuxcontainers.org"; then
  log "images-Remote hinzufügen"
  incus remote add images https://images.linuxcontainers.org \
    --protocol=simplestreams --public 2>&1 | tail -2 || true
fi

# Nested-LXC-Detection: wenn HH2 selbst in LXC läuft → privileged-Default
if [ "$(systemd-detect-virt 2>/dev/null)" = "lxc" ]; then
  log "Nested-LXC erkannt — default-Profil auf privileged + nesting"
  incus profile set default security.privileged true 2>&1 || true
  incus profile set default security.nesting true 2>&1 || true
else
  log "Bare-Metal/VM-Host — default-Profil bleibt unprivileged"
fi

# hydrahive-User in incus-admin (sonst geht der incus-Aufruf nur als root)
if getent group incus-admin >/dev/null; then
  if id -nG "$HH_USER" | grep -qw incus-admin; then
    log "User '$HH_USER' bereits in 'incus-admin'"
  else
    log "User '$HH_USER' zur Gruppe 'incus-admin' hinzufügen"
    usermod -aG incus-admin "$HH_USER"
  fi
fi

# incus liest $HOME/.config/incus/config.yml beim ersten Aufruf — wenn das
# Verzeichnis nicht da oder nicht lesbar ist, schlägt jeder Befehl fehl.
HH_HOME="/home/$HH_USER"
if [ -d "$HH_HOME" ]; then
  mkdir -p "$HH_HOME/.config/incus"
  chown -R "$HH_USER:$HH_USER" "$HH_HOME/.config"
  chmod 755 "$HH_HOME/.config"
  chmod 700 "$HH_HOME/.config/incus"
fi

# Service-File patchen: SupplementaryGroups=incus-admin
SERVICE_FILE=/etc/systemd/system/hydrahive2.service
if [ -f "$SERVICE_FILE" ]; then
  if ! grep -q "SupplementaryGroups=.*incus-admin" "$SERVICE_FILE"; then
    log "SupplementaryGroups erweitern um incus-admin"
    if grep -q "^SupplementaryGroups=" "$SERVICE_FILE"; then
      sed -i 's|^SupplementaryGroups=\(.*\)|SupplementaryGroups=\1 incus-admin|' "$SERVICE_FILE"
    else
      sed -i '/^\[Service\]/a SupplementaryGroups=incus-admin' "$SERVICE_FILE"
    fi
    systemctl daemon-reload
    systemctl restart hydrahive2.service || true
  fi
fi

# br0-Check: für Container-Bridged genau wie für VMs
if ! ip link show br0 >/dev/null 2>&1; then
  log "WARNUNG: br0 fehlt — bridged Container starten nicht. setup-bridge.sh ausführen."
fi

log "Container-Setup fertig (incus $(incus version 2>/dev/null | head -1))"
