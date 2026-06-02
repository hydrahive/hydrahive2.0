#!/usr/bin/env bash
# Bridge-Setup für VM-Networking (br0 mit DHCP).
#
# WARNUNG: Schaltet das Default-Interface auf eine Bridge um. Eine laufende
# SSH-Verbindung kann kurz hängen während netplan die Konfig anwendet.
# Idealerweise lokal oder aus `tmux` ausführen, sonst via Out-of-Band-Console.
#
# Idempotent: erkennt vorhandene br0 und tut nichts.
set -euo pipefail

log() { printf "\033[1;36m[hh2-bridge]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[hh2-bridge]\033[0m %s\n" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Bitte mit sudo / als root ausführen."

if ip link show br0 >/dev/null 2>&1; then
  log "br0 existiert bereits — nichts zu tun."
  exit 0
fi

# Default-Route-Interface ermitteln
IFACE=$(ip -4 route show default | awk '{print $5; exit}')
[ -n "$IFACE" ] || err "Kein Default-Interface gefunden — bist du im Netzwerk?"

if [ "$IFACE" = "br0" ]; then
  log "Default-Interface ist bereits br0 — fertig."
  exit 0
fi

log "Default-Interface: $IFACE — wird in br0 enslaved."

# Aktuelle MAC-Adresse merken — für saubere DHCP-Fortsetzung
MAC=$(ip link show "$IFACE" | awk '/link\/ether/ {print $2}')

# Renderer bestimmen (#174): managt NetworkManager das Default-Interface, MUSS die
# Bridge-Config renderer: NetworkManager nutzen. Sonst baut networkd eine tote
# Bridge (NO-CARRIER), während NM das physische Interface weiter beansprucht.
RENDERER="networkd"
if systemctl is-active --quiet NetworkManager 2>/dev/null && command -v nmcli >/dev/null 2>&1; then
  NM_CONN=$(nmcli -t -f DEVICE,CONNECTION device status 2>/dev/null | awk -F: -v i="$IFACE" '$1==i {print $2}')
  if [ -n "$NM_CONN" ] && [ "$NM_CONN" != "--" ]; then
    RENDERER="NetworkManager"
    log "NetworkManager managt $IFACE (Profil '$NM_CONN') → renderer: NetworkManager"
  fi
fi
[ "$RENDERER" = "networkd" ] && log "Renderer: networkd (kein NM-Management von $IFACE erkannt)"

# netplan-Config schreiben (nur wenn noch keine Bridge-Config existiert)
CFG=/etc/netplan/99-hydrahive-bridge.yaml
if [ -f "$CFG" ]; then
  err "$CFG existiert bereits — bitte manuell prüfen, hier kein Auto-Overwrite."
fi

log "Schreibe $CFG"
cat > "$CFG" <<EOF
network:
  version: 2
  renderer: $RENDERER
  ethernets:
    $IFACE:
      dhcp4: false
      dhcp6: false
      optional: true
  bridges:
    br0:
      interfaces: [$IFACE]
      macaddress: $MAC
      dhcp4: true
      parameters:
        stp: false
        forward-delay: 0
EOF
chmod 600 "$CFG"

# Bestehende netplan-Configs für $IFACE auslassen — die könnten stören
for f in /etc/netplan/*.yaml; do
  [ "$f" = "$CFG" ] && continue
  if grep -qE "^\s+$IFACE:" "$f" 2>/dev/null; then
    log "Bestehende Config $f referenziert $IFACE — auf .disabled umbenennen"
    mv "$f" "$f.disabled-by-hydrahive"
  fi
done

log "netplan generate (Syntax-Check)"
netplan generate

log "netplan apply (Bridge wird aktiv — SSH kann kurz hängen, kommt zurück)"
netplan apply

sleep 3
if ip link show br0 >/dev/null 2>&1; then
  log "br0 ist aktiv."
  ip -4 addr show br0 | grep -E "^\s+inet " | head -1
else
  err "br0 nach netplan apply nicht da — bitte 'journalctl -u systemd-networkd' prüfen."
fi
