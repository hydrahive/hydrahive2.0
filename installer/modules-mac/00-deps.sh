#!/usr/bin/env bash
set -euo pipefail
log() { printf "  · %s\n" "$*"; }

eval "$(/usr/local/bin/brew shellenv zsh 2>/dev/null || /opt/homebrew/bin/brew shellenv zsh 2>/dev/null || true)"

BREW_PKGS=(python@3.12 node git ffmpeg gh)

for pkg in "${BREW_PKGS[@]}"; do
  if brew list "$pkg" &>/dev/null; then
    log "$pkg bereits installiert"
  else
    log "brew install $pkg"
    brew install "$pkg" --quiet
  fi
done

# uv (für uvx / MCP-Server)
if ! command -v uvx >/dev/null 2>&1; then
  log "Installiere uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
fi

# mmx CLI
if ! command -v mmx >/dev/null 2>&1; then
  log "Installiere mmx-cli"
  npm install -g mmx-cli --silent
fi

log "Dependencies bereit."
