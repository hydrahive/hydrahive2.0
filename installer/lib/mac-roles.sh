#!/bin/bash
# macOS: zwei Rollen im Installer (docs/plans/mac-service-user.md) – zum Einbinden per `source`.
#
#   HH_BREW_USER – Besitzer von Homebrew. brew verweigert root und gehört dem Menschen am Mac.
#                  Ohne Angabe: beim System-Konto (Name mit „_“, macOS-Brauch wie _www) der Besitzer der brew-Datei
#                  (so braucht das Update als root keine Einstellung); sonst wie bisher HH_USER.
#   HH_USER      – Dienst-Konto: Besitzer von Repo/Daten/Config, unter ihm laufen die Dienste
#                  (neu: verstecktes Konto _hydrahive; alte Installationen: der Mac-Besitzer).
#
# as_brew / as_svc führen direkt aus, wenn der Aufrufer schon die Rolle hat (alter Weg: beide Rollen = ein
# Nutzer → nichts ändert sich), sonst über sudo -u. as_svc setzt HOME auf das Home des Kontos (pip-, npm-,
# lima-Caches) und reicht PATH durch (sudo setzt sonst einen PATH ohne Homebrew).
HH_USER="${HH_USER:?HH_USER fehlt}"

if [ -z "${HH_BREW:-}" ]; then
  for _hh_candidate in ${HH_BREW_CANDIDATES:-/opt/homebrew/bin/brew /usr/local/bin/brew}; do
    if [ -x "$_hh_candidate" ]; then HH_BREW="$_hh_candidate"; break; fi
  done
  [ -n "${HH_BREW:-}" ] || HH_BREW="$(command -v brew || echo brew)"
fi

_hh_owner() {   # BSD-stat (macOS) vs. GNU-stat (Tests unter Linux)
  if [ "$(uname)" = "Darwin" ]; then stat -f %Su "$1" 2>/dev/null; else stat -c %U "$1" 2>/dev/null; fi
}
if [ -z "${HH_BREW_USER:-}" ]; then
  case "$HH_USER" in
    _*) HH_BREW_USER="$(_hh_owner "$(readlink -f "$HH_BREW" 2>/dev/null || echo "$HH_BREW")" || true)"
        [ -n "$HH_BREW_USER" ] && [ "$HH_BREW_USER" != "root" ] || HH_BREW_USER="$HH_USER" ;;
    *)  HH_BREW_USER="$HH_USER" ;;
  esac
fi
export HH_BREW HH_BREW_USER

as_root() { [ "$(id -u)" -eq 0 ]; }
priv() { if as_root; then "$@"; else sudo "$@"; fi; }

hh_svc_home() {
  local h
  h="$(dscl . -read "/Users/$HH_USER" NFSHomeDirectory 2>/dev/null | awk '{print $2}' || true)"
  echo "${h:-/Users/$HH_USER}"
}

# Läuft HydraHive unter einem eigenen Konto (nicht dem Mac-Besitzer)?
hh_service_account() { [ "$HH_USER" != "$HH_BREW_USER" ]; }

as_svc() {
  if [ "$(id -un)" = "$HH_USER" ]; then "$@"; return; fi
  sudo -u "$HH_USER" env "PATH=$PATH" "HOME=$(hh_svc_home)" "$@"
}

as_brew() {
  if [ "$(id -un)" = "$HH_BREW_USER" ]; then "$HH_BREW" "$@"; return; fi
  sudo -u "$HH_BREW_USER" "$HH_BREW" "$@"
}

# install.conf (Merker der Installation) liegt im Config-Ordner des Dienst-Kontos (0770, Mac-Besitzer nicht drin):
# immer über priv lesen. Ohne sudo hielt der Installer die Datei für leer und überschrieb die anderen Merker.
hh_conf_get() {   # $1=Datei $2=Schlüssel → Wert (Exit 1, wenn nicht gesetzt)
  local line
  line="$(priv cat "$1" 2>/dev/null | grep "^$2=" | tail -1)" || return 1
  [ -n "$line" ] || return 1
  printf '%s\n' "${line#*=}"
}
hh_conf_set() {   # $1=Datei $2=Schlüssel $3=Wert – andere Zeilen bleiben, Besitzer = Dienst-Konto, 0640
  local tmp
  tmp="$(mktemp)"
  { priv cat "$1" 2>/dev/null | grep -v "^$2=" || true; echo "$2=$3"; } > "$tmp"
  priv install -m 0640 "$tmp" "$1"
  rm -f "$tmp"
  priv chown "$HH_USER" "$1"
}
