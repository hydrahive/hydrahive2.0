#!/usr/bin/env bash
# Auswahl der Zusatz-Module (docs/specs/installer-core-first.md §1, §2). Wird gesourct von install.sh und update.sh.
#
# Kern (immer, keine Auswahl): Backend, Oberfläche, PostgreSQL, nginx, HydraLink.
# Zusatz-Module: standardmäßig AUS bei neuen Installationen; später im Admin-Cockpit nachinstallierbar.
# Reihenfolge: ENV > install.conf > --with/--all > Standard „no“.

# Modulname (für --with und das Cockpit) → Variable. Feste Liste, nichts anderes wird angenommen.
HH_ADDONS="tailscale voice containers vms samba whatsapp local_media"

hh_addon_var() {
  case "$1" in
    tailscale)   echo HH_INSTALL_TAILSCALE ;;
    voice)       echo HH_INSTALL_VOICE ;;
    containers)  echo HH_INSTALL_CONTAINERS ;;
    vms)         echo HH_INSTALL_VMS ;;
    samba)       echo HH_INSTALL_SAMBA ;;
    whatsapp)    echo HH_INSTALL_WHATSAPP ;;
    local_media) echo HH_INSTALL_LOCAL_MEDIA ;;
    *) return 1 ;;
  esac
}

HH_CHOICES_ALL=0
HH_CHOICES_WITH=""

# Optionen aus der Kommandozeile: --all (bisheriges Verhalten) und --with=a,b,c. Unbekanntes in --with → Abbruch.
hh_choices_parse_args() {
  local arg name
  for arg in "$@"; do
    case "$arg" in
      --all) HH_CHOICES_ALL=1 ;;
      --with=*)
        for name in $(printf '%s' "${arg#--with=}" | tr ',' ' '); do
          hh_addon_var "$name" >/dev/null || {
            printf 'Unbekanntes Zusatz-Modul in --with: %s (erlaubt: %s)\n' "$name" "$HH_ADDONS" >&2
            return 1
          }
          HH_CHOICES_WITH="$HH_CHOICES_WITH $name"
        done
        ;;
    esac
  done
}

# Setzt jede noch leere Modul-Variable: --with → yes, --all → yes (außer Local Media), sonst no.
hh_choices_apply_defaults() {
  local name var value
  for name in $HH_ADDONS; do
    var="$(hh_addon_var "$name")"
    [ -n "${!var:-}" ] && continue
    value=no
    case " $HH_CHOICES_WITH " in *" $name "*) value=yes ;; esac
    if [ "$HH_CHOICES_ALL" = "1" ] && [ "$name" != "local_media" ]; then value=yes; fi
    export "$var=$value"
  done
  # Voice braucht den Container-Manager (STT läuft in incus).
  if [ "${HH_INSTALL_VOICE:-no}" = "yes" ] && [ "${HH_INSTALL_CONTAINERS:-no}" != "yes" ]; then
    export HH_INSTALL_CONTAINERS=yes
  fi
}

# Genau eine Zeile KEY='yes|no' in install.conf setzen (ersetzen oder anhängen). Nur HH_INSTALL_* und yes/no.
hh_conf_set() {
  local conf="$1" key="$2" value="$3" tmp
  case "$key" in HH_INSTALL_[A-Z]*) ;; *) printf 'hh_conf_set: unerlaubter Schlüssel %s\n' "$key" >&2; return 1 ;; esac
  case "$key" in *[!A-Z_]*) printf 'hh_conf_set: unerlaubter Schlüssel %s\n' "$key" >&2; return 1 ;; esac
  case "$value" in yes|no) ;; *) printf 'hh_conf_set: unerlaubter Wert %s\n' "$value" >&2; return 1 ;; esac
  [ -f "$conf" ] || { mkdir -p "$(dirname "$conf")"; : > "$conf"; chmod 600 "$conf"; }
  tmp="$(mktemp "${conf}.XXXXXX")"
  if grep -q "^${key}=" "$conf"; then
    sed "s|^${key}=.*|${key}='${value}'|" "$conf" > "$tmp"
  else
    cat "$conf" > "$tmp"
    printf "%s='%s'\n" "$key" "$value" >> "$tmp"
  fi
  chmod --reference="$conf" "$tmp" 2>/dev/null || chmod 600 "$tmp"
  mv "$tmp" "$conf"
}

# update.sh: Soll das Modul gepflegt werden? Schreibt das Ergebnis nach install.conf (Spec §2).
#   installiert            → yes (auch wenn „no“ drinstand: update.sh hat es bisher trotzdem installiert)
#   nicht inst., Wert da   → bleibt
#   nicht inst., kein Wert → yes (bisheriger Standard für bestehende Server)
# Aufruf: hh_addon_wanted <install.conf> <VAR> <true|false (installiert)>
hh_addon_wanted() {
  local conf="$1" var="$2" installed="$3" current
  current="${!var:-}"
  if [ "$installed" = "true" ]; then
    [ "$current" = "yes" ] || hh_conf_set "$conf" "$var" yes
    export "$var=yes"
    return 0
  fi
  if [ -z "$current" ]; then
    hh_conf_set "$conf" "$var" yes
    export "$var=yes"
    return 0
  fi
  [ "$current" = "yes" ]
}
