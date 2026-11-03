#!/bin/bash
# Lokale PDF-/OCR-Werkzeuge für bestehende Ubuntu-/Debian-Installationen.
set -euo pipefail

PACKAGES=(poppler-utils tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng)
missing=()

for package in "${PACKAGES[@]}"; do
  if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -qx "install ok installed"; then
    missing+=("$package")
  fi
done

if [ "${#missing[@]}" -eq 0 ]; then
  printf "  · PDF-Text und lokale OCR bereits installiert.\n"
  exit 0
fi

printf "  · Installiere Dokument-Werkzeuge: %s\n" "${missing[*]}"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing[@]}"
