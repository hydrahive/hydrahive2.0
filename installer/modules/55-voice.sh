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
if ! command -v mmx >/dev/null 2>&1; then
  log "Installiere mmx-cli (npm-global)"
  npm install -g mmx-cli --silent 2>&1 | tail -3 || \
    log "mmx-cli-Install fehlgeschlagen — TTS via MiniMax nicht verfügbar"
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
    apt-get update -qq
    apt-get install -y -qq python3-venv ffmpeg
    python3 -m venv /opt/wyoming
    /opt/wyoming/bin/pip install --quiet --upgrade pip
    /opt/wyoming/bin/pip install --quiet wyoming-faster-whisper
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

  log "incus-proxy-device: Container:$STT_PORT → Host:127.0.0.1:$STT_PORT"
  incus config device add "$CT_NAME" stt-port proxy \
    listen=tcp:127.0.0.1:$STT_PORT \
    connect=tcp:127.0.0.1:$STT_PORT >/dev/null
else
  log "STT-Container '$CT_NAME' existiert bereits"
  # Falls nicht running: starten
  if ! incus list --format=csv -c n,s 2>/dev/null | grep -qx "$CT_NAME,RUNNING"; then
    log "Container '$CT_NAME' nicht running — starte"
    incus start "$CT_NAME" 2>&1 | tail -3 || true
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
  log "STT noch nicht erreichbar — Container läuft im Hintergrund weiter"
  log "Diagnose: 'incus exec $CT_NAME -- journalctl -u wyoming-whisper -n 30'"
fi

# ── Migration: alten Docker-STT-Container entfernen wenn neuer läuft ─────
# Nur ausführen wenn neuer Container healthy ist — sonst Voice-Downtime.
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
