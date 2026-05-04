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

# ── STT-Container anlegen falls noch nicht da ─────────────────────────────
if ! incus list --format=csv -c n 2>/dev/null | grep -qx "$CT_NAME"; then
  log "STT-Container '$CT_NAME' anlegen (Ubuntu 24.04 LXC)"
  incus launch images:ubuntu/24.04 "$CT_NAME"

  log "Warte auf Container-Netzwerk"
  for i in $(seq 1 30); do
    if incus exec "$CT_NAME" -- getent hosts deb.debian.org >/dev/null 2>&1 \
       || incus exec "$CT_NAME" -- ping -c1 -W1 1.1.1.1 >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  log "Wyoming-Faster-Whisper installieren (pip + ffmpeg)"
  incus exec "$CT_NAME" -- bash -c "
    set -e
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y python3-venv ffmpeg
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
    log "Entferne auch alten Docker-TTS-Container (Piper) — TTS läuft via mmx-CLI"
    docker rm -f hydrahive2-tts >/dev/null 2>&1 || true
  fi
fi

log "Voice Interface bereit (STT: incus-Container '$CT_NAME' Port $STT_PORT, TTS: mmx-CLI)"
