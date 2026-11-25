#!/usr/bin/env bash
# install.conf sicher laden (Task 42a25db7, Security-Review #762). Gesourct von install.sh und update.sh.
#
# install.conf liegt in HH_CONFIG_DIR und ist vom Dienstnutzer beschreibbar; geladen wird sie aber von root. Früher wurde
# JEDER Schlüssel exportiert – damit hätte die Datei z. B. HH_SUDOERS_FILE/HH_UNIT_FILE/HH_NGINX_SITE (wohin root beim
# Rückweg schreibt) oder HH_SYSTEM_PYTHON (was root ausführt) bestimmt. Jetzt: nur eine feste Liste bekannter Schlüssel,
# jeder mit Wertprüfung. Alles andere wird ignoriert (nur der Name kommt ins Log, nie der Wert).
# Bewusst NICHT erlaubt: HH_HOST/HH_PORT (der Installer schreibt sie nie; HH_HOST=0.0.0.0 würde beim Neuschreiben der Unit
# den Dienst nach außen öffnen) und alle Pfad-/Programm-Variablen. Wer die braucht, setzt sie beim Aufruf (ENV).
# Reihenfolge bleibt: ENV > install.conf – eine schon gesetzte Variable wird nicht überschrieben.

# Prüft Schlüssel und Wert. 0 = übernehmen, 1 = ignorieren.
hh_conf_key_ok() {
  local key="$1" value="$2"
  case "$key" in
    HH_INSTALL_TAILSCALE|HH_INSTALL_POSTGRES|HH_INSTALL_VOICE|HH_INSTALL_CONTAINERS|HH_INSTALL_VMS|\
    HH_INSTALL_AGENTLINK|HH_INSTALL_NGINX|HH_INSTALL_SAMBA|HH_INSTALL_WHATSAPP|HH_INSTALL_LOCAL_MEDIA|\
    HH_INSTALL_SEARXNG|HH_SYSTEM_UPGRADE)
      case "$value" in yes|no) return 0 ;; esac ;;
    HH_TAILSCALE_AUTHKEY)
      case "$value" in ''|*[!A-Za-z0-9_-]*) return 1 ;; *) return 0 ;; esac ;;
  esac
  return 1
}

# hh_load_install_conf <datei>: bekannte Schlüssel exportieren (wenn noch nicht gesetzt), Rest ignorieren.
hh_load_install_conf() {
  local file="$1" key value ignored=""
  [ -f "$file" ] || return 0
  while IFS='=' read -r key value || [ -n "$key" ]; do
    case "$key" in ''|\#*) continue ;; esac
    value="${value#\"}"; value="${value%\"}"
    value="${value#\'}"; value="${value%\'}"
    if ! hh_conf_key_ok "$key" "$value"; then
      # Nur Namen aus Wortzeichen ins Log (keine Steuerzeichen/Werte aus einer fremd beschreibbaren Datei).
      case "$key" in *[!A-Za-z0-9_]*) ignored="$ignored <ungültig>" ;; *) ignored="$ignored $key" ;; esac
      continue
    fi
    if [ -z "${!key:-}" ]; then
      export "$key=$value"
    fi
  done < "$file"
  if [ -n "$ignored" ]; then
    printf '[install.conf] ignoriert (unbekannt oder ungültiger Wert):%s\n' "$ignored" >&2
  fi
  return 0
}
