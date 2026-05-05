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
  # sshpass: für Master-Agent-Server-Operations mit Passwort-SSH ohne pexpect-Bauten
  sshpass
)

log() { printf "  · %s\n" "$*"; }

# Bootstrap: curl + ca-certificates müssen VOR NodeSource/uv da sein.
# Auf wirklich frischem Ubuntu/Debian fehlt curl noch.
if ! command -v curl >/dev/null 2>&1; then
  log "Bootstrap: apt update + curl + ca-certificates (für NodeSource/uv-Setup)"
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y curl ca-certificates gnupg
fi

# NodeSource-Repo für aktuelles Node.js (Ubuntu liefert oft veraltete Version)
if ! command -v node >/dev/null 2>&1 || [ "$(node -v 2>/dev/null | cut -d. -f1 | tr -d v)" -lt 20 ]; then
  log "Installiere Node.js 20 LTS via NodeSource"
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null
fi

# Python 3.12 falls nicht da: über deadsnakes-PPA für Ubuntu < 24.04
if ! command -v python3.12 >/dev/null 2>&1; then
  log "Installiere Python 3.12 via deadsnakes-PPA"
  apt-get install -y software-properties-common
  add-apt-repository -y ppa:deadsnakes/ppa
fi

log "apt update"
apt-get update

log "apt install: ${REQUIRED_PACKAGES[*]}"
DEBIAN_FRONTEND=noninteractive apt-get install -y "${REQUIRED_PACKAGES[@]}"

# uv für Python-MCP-Server (uvx)
if ! command -v uvx >/dev/null 2>&1; then
  log "Installiere uv (für uvx-MCP-Server)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # uv landet in /root/.local/bin oder /home/.../.local/bin — ist nicht im Service-PATH
  # → auch global verfügbar machen
  if [ -f /root/.local/bin/uvx ]; then
    cp /root/.local/bin/uvx /usr/local/bin/uvx
    cp /root/.local/bin/uv /usr/local/bin/uv
  fi
fi

# gh CLI (GitHub) — Agent kann darüber Issues, PRs etc. anlegen wenn ein
# Project-Repo-Token konfiguriert ist (GH_TOKEN-ENV setzt der shell_exec-Tool).
if ! command -v gh >/dev/null 2>&1; then
  log "Installiere gh-cli (GitHub) via offizielles Repo"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | gpg --dearmor -o /etc/apt/keyrings/githubcli-archive-keyring.gpg
  chmod 644 /etc/apt/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y gh
fi

# mmx CLI (MiniMax official CLI für Bild/Video/Musik-Generierung + TTS)
if ! command -v mmx >/dev/null 2>&1; then
  log "Installiere mmx-cli (MiniMax CLI)"
  npm install -g mmx-cli --no-fund --no-audit
fi
# `mmx auth login` läuft NICHT hier — als root würde der Token in /root/.mmx/
# landen, der Backend-Service liest aber /home/$HH_USER/.mmx/. 55-voice.sh
# führt das als $HH_USER aus (nach 10-user.sh existiert der User).

log "Dependencies bereit."
