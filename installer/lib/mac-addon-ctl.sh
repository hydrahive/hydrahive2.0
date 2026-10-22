#!/bin/bash
# macOS: Zusatz-Module aus dem Admin-Cockpit nachinstallieren – Gegenstück zu installer/addon-ctl.sh (Linux).
#
# Gestartet vom LaunchDaemon io.hydrahive.addon (root), sobald die API $HH_DATA_DIR/.addon_request schreibt.
# Auf dem Mac sind nur „install containers“, „install voice“ und „install tailscale“ erlaubt
# (docs/plans/mac-containers.md, mac-voice.md, mac-tailscale.md); alles andere wird verworfen.
# Gleiches Log-Format wie Linux, damit das Fenster im Cockpit unverändert funktioniert.
set -uo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
HH_USER="${HH_USER:-$(ls -ld "$HH_REPO_DIR" 2>/dev/null | awk '{print $3}')}"
HH_BACKEND_PLIST="${HH_BACKEND_PLIST:-/Library/LaunchDaemons/io.hydrahive.backend.plist}"
export HH_REPO_DIR HH_DATA_DIR HH_CONFIG_DIR HH_USER

REQUEST="$HH_DATA_DIR/.addon_request"
say() { printf '[hh2-addon] %s\n' "$*"; }

[ -f "$REQUEST" ] || exit 0
request="$(head -c 64 "$REQUEST")"
trap 'rm -f "$REQUEST"' EXIT

say "===== $(date '+%F %T') Anfrage: $(printf '%s' "$request" | tr -c '[:alnum:] _-' '?') ====="

# Feste Liste: Modulname → Skript. Nur diese gibt es auf dem Mac.
addon=""
if [[ "$request" =~ ^install\ (containers|voice|tailscale)[[:space:]]*$ ]]; then
  addon="${BASH_REMATCH[1]}"
fi
case "$addon" in
  containers) script=70-containers.sh ;;
  voice)      script=55-voice.sh ;;
  tailscale)  script=80-tailscale.sh ;;
  *) say "FEHLER: auf dem Mac nur „install containers“, „install voice“ oder „install tailscale“ erlaubt – Anfrage verworfen."
     exit 2 ;;
esac
if [ -z "$HH_USER" ] || [ "$HH_USER" = "root" ]; then
  say "FEHLER: Dienstnutzer unbekannt (Besitzer von $HH_REPO_DIR)."
  exit 2
fi

say "Installiere $addon (modules-mac/$script)"
if ! bash "$HH_REPO_DIR/installer/modules-mac/$script"; then
  say "FEHLER: install $addon fehlgeschlagen — siehe oben. Nichts eingeschaltet."
  exit 1
fi

# Backend-plist neu schreiben (PATH mit incus/colima bzw. tailscale) und Backend neu laden.
say "Backend neu starten (PATH mit den neuen Werkzeugen)"
HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" HH_CONFIG_DIR="$HH_CONFIG_DIR" HH_REPO_DIR="$HH_REPO_DIR" \
  HH_HOST="${HH_HOST:-127.0.0.1}" HH_PORT="${HH_PORT:-8001}" HH_BACKEND_PLIST="$HH_BACKEND_PLIST" \
  bash "$HH_REPO_DIR/installer/modules-mac/50-launchd.sh" || {
    say "FEHLER: install $addon ok, aber Backend-Neustart fehlgeschlagen — Update im Cockpit starten."
    exit 1
  }
say "FERTIG: install $addon ok"
exit 0
