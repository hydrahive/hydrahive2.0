#!/usr/bin/env bash
# Installiert apt-Dependencies. Idempotent.
set -euo pipefail

# Locale für apt sauber setzen (Warnings sonst stören die Logs)
export LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive

# npm absichtlich NICHT in der Liste — NodeSource liefert npm mit nodejs zusammen.
# Das Ubuntu-npm-Paket konfligiert sonst: "nodejs : Conflicts: npm".
REQUIRED_PACKAGES=(
  python3.12
  python3.12-venv
  python3-pip
  nodejs
  git
  curl
  # ffmpeg + ffprobe: Voice-Stack — am Host für STT-Pre-Processing (mp4→pcm)
  # und TTS-Post-Processing (mp3→ogg/opus + Waveform-RMS für WhatsApp ptt).
  # Im STT-LXC-Container nochmal separat installiert (siehe 55-voice.sh).
  ffmpeg
)

log() { printf "  · %s\n" "$*"; }

# NodeSource-Repo für aktuelles Node.js (Ubuntu liefert oft veraltete Version)
if ! command -v node >/dev/null 2>&1 || [ "$(node -v 2>/dev/null | cut -d. -f1 | tr -d v)" -lt 20 ]; then
  log "Installiere Node.js 20 LTS via NodeSource"
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null
fi

# Python 3.12 falls nicht da: über deadsnakes-PPA für Ubuntu < 24.04
if ! command -v python3.12 >/dev/null 2>&1; then
  log "Installiere Python 3.12 via deadsnakes-PPA"
  apt-get install -y software-properties-common >/dev/null
  add-apt-repository -y ppa:deadsnakes/ppa >/dev/null
fi

log "apt update"
apt-get update -qq

log "apt install: ${REQUIRED_PACKAGES[*]}"
DEBIAN_FRONTEND=noninteractive apt-get install -y "${REQUIRED_PACKAGES[@]}" >/dev/null

# uv für Python-MCP-Server (uvx)
if ! command -v uvx >/dev/null 2>&1; then
  log "Installiere uv (für uvx-MCP-Server)"
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
  # uv landet in /root/.local/bin oder /home/.../.local/bin — ist nicht im Service-PATH
  # → auch global verfügbar machen
  if [ -f /root/.local/bin/uvx ]; then
    cp /root/.local/bin/uvx /usr/local/bin/uvx
    cp /root/.local/bin/uv /usr/local/bin/uv
  fi
fi

# mmx CLI (MiniMax official CLI für Bild/Video/Musik-Generierung und Vision)
if ! command -v mmx >/dev/null 2>&1; then
  log "Installiere mmx-cli (MiniMax CLI)"
  npm install -g mmx-cli --silent
fi
if [ -n "${MINIMAX_API_KEY:-}" ]; then
  mmx auth login --api-key "${MINIMAX_API_KEY}" --non-interactive >/dev/null 2>&1 \
    && log "mmx auth OK" || log "mmx auth fehlgeschlagen (Key prüfen)"
else
  log "MINIMAX_API_KEY nicht gesetzt — mmx auth login später manuell ausführen"
fi

log "Dependencies bereit."
