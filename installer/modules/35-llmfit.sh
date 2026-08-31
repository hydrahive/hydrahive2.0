#!/usr/bin/env bash
# Installiert die für den Ollama-Modellkatalog verwendete llmfit-CLI reproduzierbar.
set -euo pipefail

LLMFIT_VERSION="1.1.12"
TARGET="/usr/local/bin/llmfit"

log() { printf "\033[1;36m[hh2-llmfit]\033[0m %s\n" "$*"; }

current_version=""
if [ -x "$TARGET" ]; then
  current_version="$($TARGET --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
fi
if [ "$current_version" = "$LLMFIT_VERSION" ]; then
  log "llmfit $LLMFIT_VERSION ist bereits installiert"
  exit 0
fi

case "$(uname -m)" in
  x86_64|amd64)
    arch="x86_64"
    checksum="6a97338862c87e497c844ccd29a16512a147335631c179744b4f6cc87a36ead1"
    ;;
  aarch64|arm64)
    arch="aarch64"
    checksum="2407cfc625aaa4823d4eb994533b15b6f71acda2646b18368a75313462962610"
    ;;
  *)
    log "Nicht unterstützte Architektur $(uname -m) — Hardware-Fit bleibt optional"
    exit 1
    ;;
esac

archive="llmfit-v${LLMFIT_VERSION}-${arch}-unknown-linux-gnu.tar.gz"
url="https://github.com/AlexsJones/llmfit/releases/download/v${LLMFIT_VERSION}/${archive}"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

log "Lade llmfit $LLMFIT_VERSION für $arch"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
  --output "$tmp_dir/$archive" "$url"
printf '%s  %s\n' "$checksum" "$tmp_dir/$archive" | sha256sum --check --status

dir="llmfit-v${LLMFIT_VERSION}-${arch}-unknown-linux-gnu"
tar -xzf "$tmp_dir/$archive" -C "$tmp_dir" --strip-components=1 "$dir/llmfit"
install -o root -g root -m 0755 "$tmp_dir/llmfit" "$TARGET"
"$TARGET" --version >/dev/null
log "llmfit $LLMFIT_VERSION installiert"
