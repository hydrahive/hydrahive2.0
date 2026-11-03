#!/bin/bash
# Lokale PDF-/OCR-Werkzeuge für macOS. Homebrew gehört dem Mac-Besitzer,
# HydraHive läuft auf neuen Installationen dagegen als _hydrahive.
set -euo pipefail

LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=mac-roles.sh
source "$LIB/mac-roles.sh"

log() { printf "  · %s\n" "$*"; }

ensure_formula() {
  local formula="$1"
  if as_brew list --versions "$formula" >/dev/null 2>&1; then
    log "$formula bereits installiert"
  else
    log "brew install $formula"
    as_brew install "$formula" --quiet
  fi
}

ensure_formula poppler
ensure_formula tesseract
ensure_formula tesseract-lang

for command_name in pdfinfo pdftotext pdftoppm tesseract; do
  command -v "$command_name" >/dev/null 2>&1 \
    || { echo "Dokument-Werkzeug fehlt nach Homebrew-Installation: $command_name" >&2; exit 1; }
done

tesseract --list-langs 2>/dev/null | grep -qx deu \
  || { echo "Deutsche Tesseract-Sprache fehlt nach Installation von tesseract-lang" >&2; exit 1; }

log "PDF-Text und lokale OCR bereit."
