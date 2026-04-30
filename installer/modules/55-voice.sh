#!/usr/bin/env bash
# Voice Interface — Wyoming faster-whisper (STT) + Piper (TTS) via Docker
# Idempotent: läuft erneut durch wenn Container schon laufen.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

# mmx-cli — npm-globales Node-Tool, von Profile-Page als TTS-Provider nutzbar
if ! command -v mmx >/dev/null 2>&1; then
  log "Installiere mmx-cli (npm-global)"
  npm install -g mmx-cli --silent 2>&1 | tail -3 || \
    log "mmx-cli-Install fehlgeschlagen — TTS via MiniMax nicht verfügbar"
fi

# Docker installieren falls nötig
if ! command -v docker >/dev/null 2>&1; then
  log "Installiere Docker"
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>/dev/null
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
  log "Docker installiert"
fi

VOICE_DIR="/opt/hydrahive2-voice"
mkdir -p "${VOICE_DIR}"

cat > "${VOICE_DIR}/docker-compose.yml" <<'COMPOSE'
services:
  stt:
    image: rhasspy/wyoming-whisper
    container_name: hydrahive2-stt
    restart: unless-stopped
    network_mode: host
    # Kein --language: per-Request via Wyoming-Protokoll, oder Auto-Detect
    # wenn der Caller nichts setzt. Sprache ist pro WhatsApp-User konfigurierbar.
    command: >
      --model small
      --uri tcp://127.0.0.1:10300
    volumes:
      - stt-data:/data

# Piper-TTS-Container historisch hier — nicht mehr genutzt seit mmx-CLI als
# einziger TTS-Provider live ist (siehe voice/tts.py). docker rm -f
# hydrahive2-tts auf bestehenden Installs falls noch da.

volumes:
  stt-data:
COMPOSE

# Alten Piper-TTS-Container wegräumen falls noch da (Migration auf mmx-CLI)
if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q '^hydrahive2-tts$'; then
  log "Entferne alten hydrahive2-tts (Piper) — TTS läuft jetzt via mmx-CLI"
  docker rm -f hydrahive2-tts >/dev/null 2>&1 || true
fi

log "Starte Wyoming STT Container"
cd "${VOICE_DIR}"
docker compose pull -q 2>/dev/null || true
docker compose up -d

log "Warte auf STT (Port 10300)..."
for i in $(seq 1 40); do
  if (echo "" | timeout 1 nc -w1 127.0.0.1 10300) >/dev/null 2>&1; then
    log "STT bereit"; break
  fi
  [ "$i" -eq 40 ] && log "STT noch nicht bereit — startet im Hintergrund"
  sleep 3
done

log "Voice Interface bereit (STT: Port 10300, TTS via mmx-CLI)"
