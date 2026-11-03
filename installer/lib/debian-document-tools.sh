#!/bin/bash
# Lokale PDF-/OCR-Werkzeuge und Bubblewrap-Parser-Sandbox für Ubuntu/Debian.
set -euo pipefail

PACKAGES=(poppler-utils tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng bubblewrap apparmor util-linux)
missing=()
DPKG_QUERY="${HH_DPKG_QUERY:-/usr/bin/dpkg-query}"
APT_GET="${HH_APT_GET:-/usr/bin/apt-get}"

for package in "${PACKAGES[@]}"; do
  if ! "$DPKG_QUERY" -W -f='${Status}' "$package" 2>/dev/null | /usr/bin/grep -qx "install ok installed"; then
    missing+=("$package")
  fi
done

if [ "${#missing[@]}" -eq 0 ]; then
  printf "  · PDF-Text, lokale OCR und Bubblewrap bereits installiert.\n"
else
  printf "  · Installiere Dokument-Werkzeuge: %s\n" "${missing[*]}"
  "$APT_GET" update
  DEBIAN_FRONTEND=noninteractive "$APT_GET" install -y "${missing[@]}"
fi

SCRIPT="${BASH_SOURCE[0]}"
LIB="${SCRIPT%/*}"
[ "$LIB" != "$SCRIPT" ] || LIB=.
LIB="$(cd "$LIB" && pwd -P)"
PROFILE_SOURCE="$LIB/hydrahive-bwrap-userns.apparmor"
PROFILE_TARGET="${HH_APPARMOR_PROFILE_TARGET:-/etc/apparmor.d/hydrahive-bwrap-userns}"
INSTALL_BIN="${HH_INSTALL_BIN:-/usr/bin/install}"
PARSER="${HH_APPARMOR_PARSER:-/usr/sbin/apparmor_parser}"
RUNUSER="${HH_RUNUSER:-/usr/sbin/runuser}"
BWRAP="${HH_BWRAP:-/usr/bin/bwrap}"

[ -f "$PROFILE_SOURCE" ] || { echo "Bubblewrap-AppArmor-Profilquelle fehlt" >&2; exit 1; }
if ! /usr/bin/cmp -s "$PROFILE_SOURCE" "$PROFILE_TARGET" 2>/dev/null; then
  "$INSTALL_BIN" -m 0644 "$PROFILE_SOURCE" "$PROFILE_TARGET"
fi
"$PARSER" -r "$PROFILE_TARGET"
"$RUNUSER" -u nobody -- "$BWRAP" --die-with-parent --new-session --unshare-all \
  --ro-bind /usr /usr --ro-bind-try /bin /bin --ro-bind-try /lib /lib --ro-bind-try /lib64 /lib64 \
  --proc /proc --dev /dev --tmpfs /tmp -- /usr/bin/true \
  || { echo "Unprivilegierte Bubblewrap-Dokumentisolation ist nicht verfügbar" >&2; exit 1; }
printf "  · Dokumentparser-Sandbox aktiv.\n"
