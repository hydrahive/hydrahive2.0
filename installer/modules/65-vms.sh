#!/usr/bin/env bash
# VM-Manager Setup: QEMU/KVM + Bridge-Helper + websockify + Service-Capabilities.
#
# Idempotent: prüft jeden Schritt einzeln, läuft beim Update wieder durch.
#
# Was hier NICHT passiert: br0-Bridge selbst anlegen — das erfordert eine
# Netzwerk-Reconfig die eine laufende SSH-Verbindung killen kann. Dafür gibt
# es das separate `installer/setup-bridge.sh`. Der Installer prüft am Ende
# ob br0 existiert und gibt sonst einen Hinweis aus.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }
HH_USER="${HH_USER:-hydrahive}"
INSTALLER_DIR="${INSTALLER_DIR:-/opt/hydrahive2/installer}"

log "QEMU + KVM-Pakete installieren"
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    qemu-system-x86 qemu-utils bridge-utils \
    websockify novnc

# qemu-bridge-helper setuid — sonst kann der Service ohne CAP_NET_ADMIN keine
# Bridge benutzen. Auf Ubuntu liegt das Binary unter /usr/lib/qemu/.
BRIDGE_HELPER=$(find /usr/lib /usr/libexec -name "qemu-bridge-helper" 2>/dev/null | head -1)
if [ -n "$BRIDGE_HELPER" ]; then
  if [ ! -u "$BRIDGE_HELPER" ]; then
    log "qemu-bridge-helper bekommt setuid"
    chmod u+s "$BRIDGE_HELPER"
  fi
else
  log "WARNUNG: qemu-bridge-helper nicht gefunden — bridged networking wird nicht funktionieren"
fi

# /etc/qemu/bridge.conf — erlaubt allen QEMU-Aufrufen die br0-Bridge
mkdir -p /etc/qemu
if ! grep -q "^allow br0" /etc/qemu/bridge.conf 2>/dev/null; then
  log "br0 in /etc/qemu/bridge.conf erlauben"
  echo "allow br0" >> /etc/qemu/bridge.conf
  chmod 644 /etc/qemu/bridge.conf
fi

# kvm + render-Gruppe — User muss in kvm sein für /dev/kvm-Zugriff
if id -nG "$HH_USER" | grep -qw kvm; then
  log "User '$HH_USER' bereits in Gruppe 'kvm'"
else
  log "User '$HH_USER' zur Gruppe 'kvm' hinzufügen"
  usermod -aG kvm "$HH_USER"
fi

# VM-Verzeichnisse mit korrektem Owner
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"
for sub in vms vms/isos vms/disks vms/pids vms/logs vms/vnc-tokens; do
  mkdir -p "$HH_DATA_DIR/$sub"
done
chown -R "$HH_USER:$HH_USER" "$HH_DATA_DIR/vms"

# systemd-Service muss /dev/kvm rw zugreifen + supplementary group kvm haben.
# Wir patchen das Service-File (von 50-systemd.sh geschrieben) wenn die
# Direktiven fehlen.
SERVICE_FILE=/etc/systemd/system/hydrahive2.service
if [ -f "$SERVICE_FILE" ]; then
  CHANGED=0
  if ! grep -q "^DeviceAllow=/dev/kvm" "$SERVICE_FILE"; then
    log "DeviceAllow=/dev/kvm in Service-File einfügen"
    sed -i '/^\[Service\]/a DeviceAllow=/dev/kvm rw' "$SERVICE_FILE"
    CHANGED=1
  fi
  if ! grep -q "^SupplementaryGroups=kvm" "$SERVICE_FILE"; then
    log "SupplementaryGroups=kvm in Service-File einfügen"
    sed -i '/^\[Service\]/a SupplementaryGroups=kvm' "$SERVICE_FILE"
    CHANGED=1
  fi
  # ReadWritePaths erweitern damit qcow2 + Pidfiles + Logs schreibbar sind —
  # ist eigentlich durch HH_DATA_DIR abgedeckt, aber expliziter macht's robust
  if [ "$CHANGED" = "1" ]; then
    systemctl daemon-reload
    systemctl restart hydrahive2.service || true
  fi
fi

# websockify-Service — broadcasted VNC-Verbindungen nach Token-Lookup auf
# 6080. Token-Files schreibt das Backend in vms/vnc-tokens/.
WS_SERVICE=/etc/systemd/system/hydrahive2-websockify.service
if [ ! -f "$WS_SERVICE" ]; then
  log "websockify-Service anlegen"
  cat > "$WS_SERVICE" <<EOF
[Unit]
Description=HydraHive2 VNC WebSocket Proxy
After=network.target

[Service]
Type=simple
User=$HH_USER
Group=$HH_USER
ExecStart=/usr/bin/websockify --token-plugin=TokenFile --token-source=$HH_DATA_DIR/vms/vnc-tokens 127.0.0.1:6080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable hydrahive2-websockify.service >/dev/null 2>&1
fi

systemctl restart hydrahive2-websockify.service || true

# br0-Check zum Schluss
if ! ip link show br0 >/dev/null 2>&1; then
  log "----------------------------------------------------------"
  log "WARNUNG: Netzwerk-Bridge 'br0' existiert nicht."
  log "Bridged-VMs starten ohne Bridge nicht. Zum automatischen Anlegen:"
  log "  sudo bash $INSTALLER_DIR/setup-bridge.sh"
  log "(SSH kann kurz unterbrechen — am besten lokal oder aus tmux ausführen)"
  log "----------------------------------------------------------"
else
  log "br0 vorhanden"
fi
