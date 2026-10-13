#!/usr/bin/env bash
# HydraHive2 — Zusatz-Module aus dem Admin-Cockpit nachinstallieren (docs/specs/installer-core-first.md §3).
#
# Aufgerufen von hydrahive2-addon.service (root), sobald die API $HH_DATA_DIR/.addon_request geschrieben hat.
# Die Datei enthält genau eine Zeile „install <modul>“. Erlaubt sind nur die Namen aus der festen Liste unten;
# alles andere wird verworfen. Aus der Oberfläche gelangen so weder Pfade noch Parameter in Shell-Code.
#
# Erst nach erfolgreicher Installation steht HH_INSTALL_<MODUL>=yes in install.conf — damit pflegt update.sh das
# Modul künftig mit. Die Anfrage bleibt bis zum Ende liegen (API meldet „läuft“, 409 bei weiterem Klick).
set -uo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/etc/hydrahive2}"
export HH_REPO_DIR HH_DATA_DIR HH_CONFIG_DIR

REQUEST="$HH_DATA_DIR/.addon_request"
INSTALL_CONF="$HH_CONFIG_DIR/install.conf"
MODULES="$HH_REPO_DIR/installer/modules"

say() { printf '[hh2-addon] %s\n' "$*"; }

# Feste Liste: Modulname → Installer-Skript. PostgreSQL ist Kern, Local Media hat seinen eigenen Weg.
addon_script() {
  case "$1" in
    containers) echo 70-containers.sh ;;
    vms)        echo 65-vms.sh ;;
    samba)      echo 47-samba.sh ;;
    whatsapp)   echo 45-whatsapp.sh ;;
    voice)      echo 55-voice.sh ;;
    tailscale)  echo 80-tailscale.sh ;;
    *) return 1 ;;
  esac
}

[ -f "$REQUEST" ] || exit 0
request="$(head -c 64 "$REQUEST")"
trap 'rm -f "$REQUEST"' EXIT

# shellcheck source=lib/install-choices.sh
source "$HH_REPO_DIR/installer/lib/install-choices.sh"

say "===== $(date '+%F %T') Anfrage: $(printf '%s' "$request" | tr -c '[:alnum:] _-' '?') ====="

# Feste Zusatz-Aktion (Archiv Etappe 1b): Platte für das System-Archiv einrichten. Nur eine 12-stellige ID; die
# Platten-Liste baut lib/archive-disk.sh selbst – kein Pfad aus der Oberfläche erreicht die Shell.
if [[ "$request" =~ ^prepare-archive\ ([0-9a-f]{12})[[:space:]]*$ ]]; then
  # shellcheck source=lib/archive-disk.sh
  source "$HH_REPO_DIR/installer/lib/archive-disk.sh"
  if hh_archive_disk_prepare "${BASH_REMATCH[1]}"; then
    say "FERTIG: prepare-archive ok"
    exit 0
  fi
  say "FEHLER: prepare-archive fehlgeschlagen — siehe oben."
  exit 1
fi

# Genau „install <name>“ – eine Zeile, ein Wort, nur aus der Liste.
addon=""
if [[ "$request" =~ ^install\ ([a-z]+)[[:space:]]*$ ]] && addon_script "${BASH_REMATCH[1]}" >/dev/null; then
  addon="${BASH_REMATCH[1]}"
fi
if [ -z "$addon" ]; then
  say "FEHLER: unbekannte Anfrage verworfen."
  exit 2
fi

# install_one <name>: Skript mit HH_INSTALL_<NAME>=yes starten; nur bei Erfolg in install.conf eintragen.
install_one() {
  local name="$1" var script
  var="$(hh_addon_var "$name")"
  script="$(addon_script "$name")"
  say "Installiere $name ($script)"
  if ! env "$var=yes" bash "$MODULES/$script"; then
    return 1
  fi
  hh_conf_set "$INSTALL_CONF" "$var" yes
}

# Voice läuft in einem incus-Container – ohne Container-Manager vorher diesen installieren.
if [ "$addon" = voice ] && ! command -v "${HH_INCUS_BIN:-incus}" >/dev/null 2>&1; then
  say "Voice braucht den Container-Manager – installiere zuerst containers"
  if ! install_one containers; then
    say "FEHLER: install voice fehlgeschlagen (containers) — siehe oben. Nichts eingeschaltet."
    exit 1
  fi
fi

if install_one "$addon"; then
  say "FERTIG: install $addon ok"
  exit 0
fi
say "FEHLER: install $addon fehlgeschlagen — siehe oben. Nichts eingeschaltet."
exit 1
