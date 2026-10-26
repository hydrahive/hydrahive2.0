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
SHARE_USER="hhshare"
DIR="$HH_CONFIG_DIR/mac-shares.d"
PROJECTS="$HH_DATA_DIR/workspaces/projects"
ACE_RW="user:$SHARE_USER allow list,add_file,search,delete,add_subdirectory,delete_child,readattr,writeattr,readextattr,writeextattr,readsecurity,file_inherit,directory_inherit"

say() { printf '[hh2-shares] %s\n' "$*"; }
state() { printf '%s\n' "$2" > "$DIR/$1.state"; }

[ -d "$DIR" ] || exit 0

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
  local old=""
  [ -f "$DIR/$id.name" ] && old="$(cat "$DIR/$id.name")"
  if [ "$mode" = "off" ]; then
    if [ -n "$old" ] && [[ "$old" =~ ^[A-Za-z0-9_-]{1,50}$ ]]; then
      sharing -r "$old" >/dev/null 2>&1 || true
    fi
    chmod -a "$ACE_RW" "$path" 2>/dev/null || true
    rm -f "$DIR/$id.name"
    state "$id" "off"; say "aus: $id"; return
  fi
  if [ "$mode" != "on" ] || ! [[ "$name" =~ ^[A-Za-z0-9_-]{1,50}$ ]]; then
    say "verworfen ($id): ungültiger Auftrag"; state "$id" "error:request"; return
  fi
  if [ -n "$old" ] && [ "$old" != "$name" ] && [[ "$old" =~ ^[A-Za-z0-9_-]{1,50}$ ]]; then
    sharing -r "$old" >/dev/null 2>&1 || true            # umbenannt: alte Freigabe weg
  fi
  chmod -a "$ACE_RW" "$path" 2>/dev/null || true         # nie doppelt
  if ! chmod +a "$ACE_RW" "$path"; then
    state "$id" "error:acl"; say "FEHLER ($id): Rechte"; return
  fi
  sharing -r "$name" >/dev/null 2>&1 || true
  if ! sharing -a "$path" -S "$name" -s 001 -g 000; then
    state "$id" "error:sharing"; say "FEHLER ($id): sharing"; return
  fi
  printf '%s\n' "$name" > "$DIR/$id.name"
  state "$id" "on"; say "an: $id als $name"
}

shopt -s nullglob
for want in "$DIR"/*.want; do
  handle "$want"
done
exit 0
