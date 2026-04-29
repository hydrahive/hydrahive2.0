#!/usr/bin/env bash
# Voice Interface — Wyoming faster-whisper (STT) + Piper (TTS) via Docker
# Idempotent: läuft erneut durch wenn Container schon laufen.
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

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
    command: >
      --model small
      --language de
      --uri tcp://127.0.0.1:10300
    volumes:
      - stt-data:/data

  tts:
    image: rhasspy/wyoming-piper
    container_name: hydrahive2-tts
    restart: unless-stopped
    network_mode: host
    command: >
      --voice de_DE-thorsten-high
      --uri tcp://127.0.0.1:10200
    volumes:
      - tts-data:/data

volumes:
  stt-data:
  tts-data:
COMPOSE

log "Starte Wyoming STT + TTS Container"
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

log "Voice Interface bereit (STT: Port 10300 | TTS: Port 10200)"
