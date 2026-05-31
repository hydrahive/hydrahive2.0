#!/usr/bin/env bash
# Voice Interface — Wyoming faster-whisper (STT) als incus-LXC + mmx-CLI (TTS)
#
# Migration vom Docker-Stack: alter Docker-STT-Container wird am Ende
# entfernt — ABER nur wenn neuer incus-Container healthy ist (kein
# Voice-Downtime). Migrations-Skript installer/migrations/voice-docker-
# to-incus.sh ist eigenständig aufrufbar für saubere Übernahme.
#
# Voraussetzungen:
# - incus läuft (kommt aus 70-containers.sh) — Daemon + dir-Storage + br0
# - Node 20 für mmx-CLI (npm-global) — kommt aus 00-deps.sh
#
# Idempotent: Container nicht angetastet wenn schon RUNNING + Port offen.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

if [ "${HH_INSTALL_VOICE:-yes}" = "no" ]; then
  log "Voice-Stack übersprungen (HH_INSTALL_VOICE=no)"
  exit 0
fi

CT_NAME="hydrahive2-stt"
STT_PORT=10300

# ── mmx-CLI (TTS) ─────────────────────────────────────────────────────────
HH_USER_VOICE="${HH_USER:-hydrahive}"
HH_HOME_VOICE="/home/$HH_USER_VOICE"

if ! command -v mmx >/dev/null 2>&1; then
  log "Installiere mmx-cli (npm-global)"
  npm install -g mmx-cli --no-fund --no-audit || \
    log "mmx-cli-Install fehlgeschlagen — TTS via MiniMax nicht verfügbar"
fi

# mmx-Auth als $HH_USER (nicht als root — Backend liest $HH_HOME/.mmx).
# Key aus /etc/hydrahive2/llm.json (Provider-ID 'minimax') statt zweite Config-Quelle.
if [ ! -d "$HH_HOME_VOICE/.mmx" ] \
   && [ -f /etc/hydrahive2/llm.json ] \
   && id "$HH_USER_VOICE" >/dev/null 2>&1; then
  MMX_KEY=$(python3 -c '
import json, sys
try:
    d = json.load(open("/etc/hydrahive2/llm.json"))
    for p in d.get("providers", []):
        if p.get("id") == "minimax":
            print(p.get("api_key", ""))
            break
except Exception:
    pass
' 2>/dev/null)
  if [ -n "$MMX_KEY" ]; then
    log "mmx auth login als $HH_USER_VOICE"
    install -d -o "$HH_USER_VOICE" -g "$HH_USER_VOICE" -m 0700 "$HH_HOME_VOICE/.mmx"
    sudo -u "$HH_USER_VOICE" HOME="$HH_HOME_VOICE" \
      mmx auth login --api-key "$MMX_KEY" --non-interactive >/dev/null 2>&1 \
      && log "mmx auth OK" \
      || log "mmx auth fehlgeschlagen (Key in llm.json prüfen)"
  else
    log "MiniMax-Key fehlt in llm.json — mmx-Auth übersprungen"
  fi
fi

# ── Voraussetzung: incus muss laufen ──────────────────────────────────────
if ! command -v incus >/dev/null 2>&1; then
  log "FEHLER: incus nicht installiert — 70-containers.sh muss vor 55-voice.sh laufen"
  exit 1
fi

# ── Container-Outbound sicherstellen ──────────────────────────────────────
# 70-containers.sh nutzt 'networks: []' (kein incus-Bridge) + Host-br0. Wo der
# Container keinen ECHTEN Outbound hat (DNS allein reicht nicht — NAT kann ohne
# Host-Forwarding auflösen aber nicht rausrouten), wird er an br0 gehängt (echtes
# LAN wie die VMs); nur wenn br0 fehlt, ein eigenes NAT-Netz als Fallback.
VOICE_NET="hh-voice"

# Echter Outbound-Test: TCP nach draußen (DNS-Auflösung allein täuscht — prod-NAT
# löst auf, routet aber nicht). 53 = DNS-over-TCP, fast überall offen.
_net_ok() { incus exec "$1" -- timeout 5 bash -c 'exec 3<>/dev/tcp/1.1.1.1/53' >/dev/null 2>&1; }

_net_wait() {  # $1=ct, $2=sekunden
  local ct="$1" n="$2" i
  for i in $(seq 1 "$n"); do _net_ok "$ct" && return 0; sleep 1; done
  return 1
}

ensure_container_net() {  # $1 = container-name; return 0 wenn ECHTER Outbound da
  local ct="$1"
  _net_ok "$ct" && return 0
  # evtl. vorhandene (tote) eth0 — z.B. NAT ohne Routing — sauber entfernen
  incus config device remove "$ct" eth0 >/dev/null 2>&1 || true
  # 1) Host-Bridge br0 bevorzugt — echtes LAN-Internet, genau wie die VMs nutzen
  if ip link show br0 >/dev/null 2>&1; then
    log "  '$ct' an Host-Bridge br0 hängen (LAN)"
    incus config device add "$ct" eth0 nic nictype=bridged parent=br0 name=eth0 2>&1 | tail -2 || true
    incus restart "$ct" 2>&1 | tail -2 || true
    _net_wait "$ct" 25 && return 0
    log "  br0 ohne Outbound — entferne wieder"
    incus config device remove "$ct" eth0 >/dev/null 2>&1 || true
  fi
  # 2) NAT-Fallback (Boxen ohne br0, z.B. Minimal-Setups)
  log "  NAT-Netz '$VOICE_NET' als Fallback"
  if ! incus network list --format=csv -c n 2>/dev/null | grep -qx "$VOICE_NET"; then
    incus network create "$VOICE_NET" ipv4.address=auto ipv4.nat=true ipv6.address=none 2>&1 | tail -2 || true
  fi
  incus config device add "$ct" eth0 nic network="$VOICE_NET" name=eth0 2>&1 | tail -2 || true
  incus restart "$ct" 2>&1 | tail -2 || true
  _net_wait "$ct" 30 && return 0
  return 1
}

# ── STT-Container anlegen falls noch nicht da ─────────────────────────────
if ! incus list --format=csv -c n 2>/dev/null | grep -qx "$CT_NAME"; then
  log "STT-Container '$CT_NAME' anlegen (Ubuntu 24.04 LXC)"
  incus launch images:ubuntu/24.04 "$CT_NAME"

  log "Container-Netzwerk sicherstellen"
  if ! ensure_container_net "$CT_NAME"; then
    log "FEHLER: STT-Container '$CT_NAME' hat kein Netz — Setup abgebrochen (br0/Netz prüfen)"
    incus delete -f "$CT_NAME" 2>/dev/null || true
    exit 1
  fi

  log "Wyoming-Faster-Whisper installieren (pip + ffmpeg)"
  incus exec "$CT_NAME" -- bash -c "
    set -e
    export DEBIAN_FRONTEND=noninteractive
    apt-get -o Acquire::ForceIPv4=true update
    apt-get -o Acquire::ForceIPv4=true install -y python3-venv ffmpeg
    python3 -m venv /opt/wyoming
    /opt/wyoming/bin/pip install --upgrade pip
    /opt/wyoming/bin/pip install wyoming-faster-whisper
  "

  log "systemd-Unit im Container schreiben"
  incus exec "$CT_NAME" -- bash -c 'cat > /etc/systemd/system/wyoming-whisper.service <<EOF
[Unit]
Description=Wyoming faster-whisper STT
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/opt/wyoming/bin/wyoming-faster-whisper --model small --uri tcp://0.0.0.0:10300 --data-dir /var/lib/wyoming
Restart=on-failure
RestartSec=5
WorkingDirectory=/var/lib/wyoming
StateDirectory=wyoming

[Install]
WantedBy=multi-user.target
EOF
mkdir -p /var/lib/wyoming
systemctl daemon-reload
systemctl enable --now wyoming-whisper.service'

else
  log "STT-Container '$CT_NAME' existiert bereits"
  if ! incus list --format=csv -c n,s 2>/dev/null | grep -qx "$CT_NAME,RUNNING"; then
    log "Container '$CT_NAME' nicht running — starte"
    incus start "$CT_NAME" 2>&1 | tail -3 || true
  fi
fi

# ── Migrations-Reihenfolge: alter Docker-Container muss Port freigeben ──
# Sonst kann incus-proxy-device nicht binden (Port already in use).
# Voice-Downtime ist die Phase zwischen "docker stop" und "Wyoming-LXC ready".
old_docker_running=0
if command -v docker >/dev/null 2>&1 \
   && docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CT_NAME"; then
  old_docker_running=1
  log "Docker-STT-Container läuft — stoppen für Port-Übergabe (kurzer Voice-Downtime)"
  docker stop "$CT_NAME" >/dev/null 2>&1 || true
fi

# ── incus-proxy-device adden falls noch nicht da ─────────────────────────
if ! incus config device show "$CT_NAME" 2>/dev/null | grep -q "^stt-port:"; then
  log "incus-proxy-device anlegen: Container:$STT_PORT → Host:127.0.0.1:$STT_PORT"
  if ! incus config device add "$CT_NAME" stt-port proxy \
        listen=tcp:127.0.0.1:$STT_PORT \
        connect=tcp:127.0.0.1:$STT_PORT 2>&1 | tail -3; then
    log "FEHLER: proxy-device-Add fehlgeschlagen"
    if [ "$old_docker_running" = "1" ]; then
      log "Rollback: alten Docker-Container wieder starten"
      docker start "$CT_NAME" >/dev/null 2>&1 || true
    fi
    exit 1
  fi
fi

# ── Health-Wait: Port 10300 erreichbar? ──────────────────────────────────
log "Warte auf STT (Port $STT_PORT)..."
ready=0
for i in $(seq 1 60); do
  if (echo "" | timeout 1 nc -w1 127.0.0.1 $STT_PORT) >/dev/null 2>&1; then
    log "STT bereit"
    ready=1
    break
  fi
  sleep 3
done

if [ "$ready" = "0" ]; then
  log "STT noch nicht erreichbar nach 180s — Diagnose:"
  log "  incus exec $CT_NAME -- journalctl -u wyoming-whisper -n 30"
  if [ "$old_docker_running" = "1" ]; then
    log "Rollback: alten Docker-Container wieder starten (Voice-Recovery)"
    incus config device remove "$CT_NAME" stt-port >/dev/null 2>&1 || true
    docker start "$CT_NAME" >/dev/null 2>&1 || true
  fi
fi

# ── Migration: alten Docker-STT-Container entfernen wenn neuer healthy ──
if [ "$ready" = "1" ] && command -v docker >/dev/null 2>&1; then
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$CT_NAME"; then
    log "Entferne alten Docker-STT-Container (Migration zu incus)"
    docker rm -f "$CT_NAME" >/dev/null 2>&1 || true
    log "Hinweis: Docker-Daemon bleibt installiert. Optional entfernen via:"
    log "  apt-get remove -y docker-ce docker-ce-cli containerd.io docker-compose-plugin"
  fi
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx hydrahive2-tts; then
    log "Entferne alten Docker-TTS-Container (Piper) — wird durch incus-LXC ersetzt"
    docker rm -f hydrahive2-tts >/dev/null 2>&1 || true
  fi
fi

# ── TTS-Container (Wyoming-Piper) als incus-LXC ───────────────────────────
# Lokales TTS ohne Cloud-Key. Spiegelbildlich zum STT-Container.
CT_TTS="hydrahive2-tts"
TTS_PORT=10200
PIPER_VOICE="${HH_PIPER_VOICE:-de_DE-thorsten-medium}"

# 1. Container existieren lassen + laufen
if ! incus list --format=csv -c n 2>/dev/null | grep -qx "$CT_TTS"; then
  log "TTS-Container '$CT_TTS' anlegen (Ubuntu 24.04 LXC)"
  incus launch images:ubuntu/24.04 "$CT_TTS"
elif ! incus list --format=csv -c n,s 2>/dev/null | grep -qx "$CT_TTS,RUNNING"; then
  log "TTS-Container '$CT_TTS' starten"
  incus start "$CT_TTS" 2>&1 | tail -3 || true
else
  log "TTS-Container '$CT_TTS' läuft"
fi

# 2. wyoming-piper installieren FALLS es fehlt (idempotent — repariert auch einen
#    bestehenden Container, in dem apt früher ohne Netz scheiterte).
if ! incus exec "$CT_TTS" -- test -x /opt/piper/bin/wyoming-piper 2>/dev/null; then
  log "Wyoming-Piper fehlt — Netz sicherstellen + installieren"
  if ! ensure_container_net "$CT_TTS"; then
    log "FEHLER: TTS-Container '$CT_TTS' hat kein Netz — Piper-Install unmöglich (br0/Netz prüfen)"
    exit 1
  fi
  incus exec "$CT_TTS" -- bash -c "
    set -e
    export DEBIAN_FRONTEND=noninteractive
    apt-get -o Acquire::ForceIPv4=true update
    apt-get -o Acquire::ForceIPv4=true install -y python3-venv
    python3 -m venv /opt/piper
    /opt/piper/bin/pip install --upgrade pip
    /opt/piper/bin/pip install wyoming-piper
  "
else
  log "Wyoming-Piper bereits installiert"
fi

# 3. systemd-Unit + Start sicherstellen (idempotent). Unit via tee schreiben —
#    kein fragiles verschachteltes Heredoc in 'incus exec'.
log "systemd-Unit sicherstellen (Voice: $PIPER_VOICE)"
printf '%s\n' \
  '[Unit]' \
  'Description=Wyoming Piper TTS' \
  'After=network-online.target' \
  'Wants=network-online.target' \
  '' \
  '[Service]' \
  'Type=simple' \
  "ExecStart=/opt/piper/bin/python -m wyoming_piper --voice ${PIPER_VOICE} --uri tcp://0.0.0.0:${TTS_PORT} --data-dir /var/lib/piper --download-dir /var/lib/piper" \
  'Restart=on-failure' \
  'RestartSec=5' \
  'WorkingDirectory=/var/lib/piper' \
  'StateDirectory=piper' \
  '' \
  '[Install]' \
  'WantedBy=multi-user.target' \
  | incus exec "$CT_TTS" -- tee /etc/systemd/system/wyoming-piper.service >/dev/null
# Voice braucht Netz zum Download beim ersten Start — sicherstellen.
ensure_container_net "$CT_TTS" >/dev/null 2>&1 || true
incus exec "$CT_TTS" -- bash -c \
  "mkdir -p /var/lib/piper && systemctl daemon-reload && systemctl enable wyoming-piper.service >/dev/null 2>&1; systemctl restart wyoming-piper.service" \
  2>&1 | tail -3 || true

if ! incus config device show "$CT_TTS" 2>/dev/null | grep -q "^tts-port:"; then
  log "incus-proxy-device anlegen: Container:$TTS_PORT → Host:127.0.0.1:$TTS_PORT"
  incus config device add "$CT_TTS" tts-port proxy \
    listen=tcp:127.0.0.1:$TTS_PORT \
    connect=tcp:127.0.0.1:$TTS_PORT 2>&1 | tail -3 || true
fi

log "Warte auf TTS (Port $TTS_PORT)..."
tts_ready=0
for i in $(seq 1 60); do
  if (echo "" | timeout 1 nc -w1 127.0.0.1 $TTS_PORT) >/dev/null 2>&1; then
    log "TTS (Piper) bereit"
    tts_ready=1
    break
  fi
  sleep 3
done

if [ "$tts_ready" = "0" ]; then
  log "WARNUNG: TTS (Piper) auf Port $TTS_PORT NICHT erreichbar — Diagnose:"
  log "  incus exec $CT_TTS -- systemctl status wyoming-piper"
  log "  incus exec $CT_TTS -- journalctl -u wyoming-piper -n 40"
  log "Voice Interface TEILWEISE bereit (STT Port $STT_PORT ok, TTS Port $TTS_PORT FEHLT)"
else
  log "Voice Interface bereit (STT: incus '$CT_NAME' Port $STT_PORT, TTS: incus '$CT_TTS' Port $TTS_PORT (Piper); MiniMax/OpenRouter optional)"
fi
