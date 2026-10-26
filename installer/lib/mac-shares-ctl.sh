#!/bin/bash
# macOS: Projekt-Freigaben umsetzen (docs/plans/mac-file-sharing.md §2.2). Läuft als root über den LaunchDaemon
# io.hydrahive.shares (WatchPaths auf $HH_CONFIG_DIR/mac-shares.d), sobald das Backend dort <id>.want schreibt.
#
# <id>.want: Zeile 1 on|off, Zeile 2 Freigabename, Zeile 3 Pfad. Angenommen wird nur, was genau passt:
#   id   [A-Za-z0-9_-]{1,64}   Name [A-Za-z0-9_-]{1,50}   Pfad == $HH_DATA_DIR/workspaces/projects/<id>, echter Ordner
# Ergebnis in <id>.state: on | off | error:<grund>. Aus der Oberfläche gelangen keine freien Werte in Shell-Befehle.
set -uo pipefail

HH_DATA_DIR="${HH_DATA_DIR:-/usr/local/var/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/usr/local/etc/hydrahive2}"
HH_USER="${HH_USER:-}"
SHARE_USER="hhshare"
DIR="$HH_CONFIG_DIR/mac-shares.d"
PROJECTS="$HH_DATA_DIR/workspaces/projects"
RIGHTS="allow list,add_file,search,delete,add_subdirectory,delete_child,readattr,writeattr,readextattr,writeextattr,readsecurity,file_inherit,directory_inherit"
ACE_RW="user:$SHARE_USER $RIGHTS"
# Was der Kunde per SMB anlegt, gehört hhshare (0600) – ohne eigenen Eintrag käme der Agent nicht mehr heran.
ACE_HH="user:$HH_USER $RIGHTS"
# Mac-Besitzer: Der Finder verbindet sich nicht per SMB mit dem eigenen Mac (live 26.10.: NetFS 65 bei jeder eigenen
# Adresse). Er bekommt das Projekt deshalb direkt: Recht darauf + Eintrag ~/HydraHive/<Freigabename>.
OWNER="${HH_MAC_OWNER:-}"
if ! [[ "$OWNER" =~ ^[A-Za-z_][A-Za-z0-9_.-]{0,31}$ ]] || [ "$OWNER" = root ] || [ "$OWNER" = "$HH_USER" ] \
   || [ "$OWNER" = "$SHARE_USER" ]; then
  OWNER=""
fi
ACE_OW="user:$OWNER $RIGHTS"

say() { printf '[hh2-shares] %s\n' "$*"; }
state() { printf '%s\n' "$2" > "$DIR/$1.state"; }

[ -d "$DIR" ] || exit 0

# Rechte für Vorhandenes nachtragen: als Dienst-Konto (kann nie mehr erreichen als dem ohnehin gehört), nie über einen
# Symlink (kein chmod -R – das folgte am echten Mac einem Link nach draußen), Links selbst bleiben unberührt.
grant_existing() {
  local path="$1" ace
  for ace in "$ACE_RW" "$ACE_HH" ${OWNER:+"$ACE_OW"}; do
    sudo -n -u "$HH_USER" find "$path" -mindepth 1 ! -type l -exec chmod -h +a "$ace" {} + 2>/dev/null || true
  done
}

# Alle Freigabe-Datensätze, deren Pfad der Projektordner ist, entfernen. `sharing -r` will den Datensatz-Namen
# (Standard: Ordnername), nicht den SMB-Namen – live 26.10. blieben so Freigaben stehen und vermehrten sich (<id>-1 …).
remove_records() {
  local rec
  while IFS= read -r rec; do
    [ -n "$rec" ] && sharing -r "$rec" >/dev/null 2>&1
  done < <(sharing -l 2>/dev/null | awk -v p="$1" '
    /^name:/ { sub(/^name:[ \t]+/, ""); n = $0 }
    /^path:/ { sub(/^path:[ \t]+/, ""); if ($0 == p) print n }')
}

owner_home() {
  local h
  h="$(dscl . -read "/Users/$OWNER" NFSHomeDirectory 2>/dev/null | awk '{print $2}')"
  case "$h" in /?*) [ -d "$h" ] && printf '%s\n' "$h" ;; esac
}

# Einträge in ~/HydraHive, die auf dieses Projekt zeigen, entfernen – nur unsere Verknüpfungen, alles andere bleibt.
# Alles im Benutzerordner läuft als Besitzer (root soll dort keinen Links folgen).
owner_unlink() {
  local path="$1" home e
  home="$(owner_home)" || return 0
  [ -n "$home" ] || return 0
  for e in "$home/HydraHive"/*; do
    [ -L "$e" ] && [ "$(readlink "$e")" = "$path" ] && sudo -n -u "$OWNER" rm -f "$e"
  done
}

owner_link() {
  local path="$1" name="$2" home
  home="$(owner_home)" || return 0
  [ -n "$home" ] || { say "Benutzerordner von $OWNER nicht gefunden"; return 0; }
  sudo -n -u "$OWNER" mkdir -p "$home/HydraHive" || return 0
  if [ -e "$home/HydraHive/$name" ] || [ -L "$home/HydraHive/$name" ]; then
    say "~/HydraHive/$name gibt es schon – nicht angefasst"; return 0
  fi
  sudo -n -u "$OWNER" ln -s "$path" "$home/HydraHive/$name" || say "Verknüpfung ~/HydraHive/$name fehlgeschlagen"
}

handle() {
  local want="$1" id mode name path real
  id="$(basename "$want" .want)"
  if ! [[ "$id" =~ ^[A-Za-z0-9_-]{1,64}$ ]]; then
    say "verworfen: ungültige Projekt-ID"; rm -f "$want"; return
  fi
  mode="$(sed -n 1p "$want" | tr -d '\r')"
  name="$(sed -n 2p "$want" | tr -d '\r')"
  path="$(sed -n 3p "$want" | tr -d '\r')"
  rm -f "$want"
  if [ "$path" != "$PROJECTS/$id" ]; then
    say "verworfen ($id): Pfad passt nicht"; state "$id" "error:path"; return
  fi
  if [ -L "$path" ] || [ ! -d "$path" ]; then
    say "verworfen ($id): kein echter Projektordner"; state "$id" "error:path"; return
  fi
  # Aufgelöster Weg muss genau Daten-Ordner/workspaces/projects/<id> sein – kein Teil des Wegs darf umgebogen sein
  # (auch nicht workspaces oder projects selbst).
  real="$(cd "$path" && pwd -P)"
  case "$real" in
    "$(cd "$HH_DATA_DIR" && pwd -P)/workspaces/projects/$id") ;;
    *) say "verworfen ($id): Pfad führt aus dem Projektbereich"; state "$id" "error:path"; return ;;
  esac
  if [ "$mode" = "off" ]; then
    remove_records "$path"
    chmod -a "$ACE_RW" "$path" 2>/dev/null || true
    if [ -n "$OWNER" ]; then
      owner_unlink "$path"
      chmod -a "$ACE_OW" "$path" 2>/dev/null || true
    fi
    rm -f "$DIR/$id.name"
    state "$id" "off"; say "aus: $id"; return
  fi
  if [ "$mode" != "on" ] || ! [[ "$name" =~ ^[A-Za-z0-9_-]{1,50}$ ]]; then
    say "verworfen ($id): ungültiger Auftrag"; state "$id" "error:request"; return
  fi
  if ! [[ "$HH_USER" =~ ^[A-Za-z_][A-Za-z0-9_.-]{0,31}$ ]] || [ "$HH_USER" = "root" ]; then
    say "FEHLER ($id): Dienst-Konto unbekannt"; state "$id" "error:user"; return
  fi
  local ace
  for ace in "$ACE_RW" "$ACE_HH" ${OWNER:+"$ACE_OW"}; do
    chmod -a "$ace" "$path" 2>/dev/null || true            # nie doppelt
    if ! chmod +a "$ace" "$path"; then
      state "$id" "error:acl"; say "FEHLER ($id): Rechte"; return
    fi
  done
  grant_existing "$path"
  remove_records "$path"                                    # alte/doppelte Datensätze (auch umbenannt) weg
  if ! sharing -a "$path" -S "$name" -n "$id" -s 001 -g 000; then
    state "$id" "error:sharing"; say "FEHLER ($id): sharing"; return
  fi
  if [ -n "$OWNER" ]; then
    owner_unlink "$path"                                    # umbenannt: alter Eintrag weg
    owner_link "$path" "$name"
  fi
  printf '%s\n' "$name" > "$DIR/$id.name"
  state "$id" "on"; say "an: $id als $name"
}

shopt -s nullglob
for want in "$DIR"/*.want; do
  handle "$want"
done
exit 0
