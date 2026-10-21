#!/bin/bash
# macOS: Zusatz-Module aus dem Admin-Cockpit nachinstallieren – Gegenstück zu installer/addon-ctl.sh (Linux).
#
# Gestartet vom LaunchDaemon io.hydrahive.addon (root), sobald die API $HH_DATA_DIR/.addon_request schreibt.
# Auf dem Mac ist nur „install containers“ erlaubt (docs/plans/mac-containers.md); alles andere wird verworfen.
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

if ! [[ "$request" =~ ^install\ containers[[:space:]]*$ ]]; then
  say "FEHLER: auf dem Mac nur „install containers“ erlaubt – Anfrage verworfen."
  exit 2
fi
if [ -z "$HH_USER" ] || [ "$HH_USER" = "root" ]; then
  say "FEHLER: Dienstnutzer unbekannt (Besitzer von $HH_REPO_DIR)."
  exit 2
fi

say "Installiere containers (modules-mac/70-containers.sh)"
if ! bash "$HH_REPO_DIR/installer/modules-mac/70-containers.sh"; then
  say "FEHLER: install containers fehlgeschlagen — siehe oben. Nichts eingeschaltet."
  exit 1
fi

# Backend-plist neu schreiben (PATH mit incus/colima) und Backend neu laden.
say "Backend neu starten (PATH mit Container-Werkzeugen)"
HH_USER="$HH_USER" HH_DATA_DIR="$HH_DATA_DIR" HH_CONFIG_DIR="$HH_CONFIG_DIR" HH_REPO_DIR="$HH_REPO_DIR" \
  HH_HOST="${HH_HOST:-127.0.0.1}" HH_PORT="${HH_PORT:-8001}" HH_BACKEND_PLIST="$HH_BACKEND_PLIST" \
  bash "$HH_REPO_DIR/installer/modules-mac/50-launchd.sh" || {
    say "FEHLER: install containers ok, aber Backend-Neustart fehlgeschlagen — Update im Cockpit starten."
    exit 1
  }
say "FERTIG: install containers ok"
exit 0
