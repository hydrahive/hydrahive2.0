#!/usr/bin/env bash
# HydraHive2 — Platte für das System-Archiv einrichten (docs/specs/archiv-system.md, Etappe 1b).
#
# Aufgerufen vom Zusatz-Module-Runner (addon-ctl.sh) als root, Anfrage „prepare-archive <id>“ aus der Admin-Konsole.
# Aus der Oberfläche kommt NUR eine 12-stellige ID. Die Platten-Liste baut dieses Skript selbst (findmnt), mit
# denselben Regeln wie core/src/hydrahive/archive/disks.py:
#   echtes lokales Dateisystem, schreibbar eingehängt, je Gerät (MAJ:MIN) einmal: „/“ zuerst, dann Einhängepunkt mit
#   echter Wurzel, dann der kürzeste (Bind-Mounts zählen mit – in Containern ist schon „/“ einer); nicht unter /boot
#   /home /root /tmp /var/tmp /proc /sys /dev /run /etc /usr und nicht unter workspaces.
#   ID = erste 12 Hex-Zeichen von sha256(einhängepunkt).
# Angelegt wird nur <einhängepunkt>/hydrahive-archiv (für / : /srv/hydrahive-archiv), Eigentümer $HH_USER, 2775.

hh_archive_disk_say() { printf '[hh2-addon] %s\n' "$*"; }

# Gesperrte Orte. Nur Tests ersetzen die Liste (HH_ARCHIVE_DISK_BLOCKED), sonst gilt dieselbe wie in disks.py.
HH_ARCHIVE_DISK_BLOCKED_DEFAULT="/boot /home /root /tmp /var/tmp /proc /sys /dev /run /etc /usr"

hh_archive_disk_blocked() {
  local m="$1" b ws="${HH_DATA_DIR:-/var/lib/hydrahive2}/workspaces"
  [ "$m" = "/" ] && return 1
  # shellcheck disable=SC2086 # Liste aus festen Pfaden ohne Leerzeichen
  for b in ${HH_ARCHIVE_DISK_BLOCKED:-$HH_ARCHIVE_DISK_BLOCKED_DEFAULT} "$ws"; do
    [ "$m" = "$b" ] && return 0
    case "$m" in "$b"/*) return 0 ;; esac
  done
  return 1
}

# Gibt „<id>\t<einhängepunkt>“ je erlaubter Platte aus.
hh_archive_disk_list() {
  local target fsroot fstype opts dev key
  declare -A best=() best_key=()
  while read -r target fsroot fstype opts dev; do
    target="$(printf '%b' "$target")"
    case "$fstype" in ext2|ext3|ext4|xfs|btrfs|zfs|f2fs|bcachefs) ;; *) continue ;; esac
    case ",$opts," in *,rw,*) ;; *) continue ;; esac
    hh_archive_disk_blocked "$target" && continue
    # Rang wie in disks.py: („/“?, echte Wurzel?, Länge) – kleiner gewinnt.
    key="$([ "$target" = "/" ] && echo 0 || echo 1)$([ "$fsroot" = "/" ] && echo 0 || echo 1)$(printf '%06d' "${#target}")"
    if [ -z "${best_key[$dev]:-}" ] || [[ "$key" < "${best_key[$dev]}" ]]; then
      best[$dev]="$target"
      best_key[$dev]="$key"
    fi
  done < <(findmnt -r -n -o TARGET,FSROOT,FSTYPE,OPTIONS,MAJ:MIN)
  local m
  for m in "${best[@]}"; do
    printf '%s\t%s\n' "$(printf '%s' "$m" | sha256sum | cut -c1-12)" "$m"
  done
}

# hh_archive_disk_prepare <id>: 0 = eingerichtet, 1 = Fehler (Grund im Log)
hh_archive_disk_prepare() {
  local id="$1" line mount="" target owner="${HH_USER:-hydrahive}"
  while IFS=$'\t' read -r line_id line; do
    [ "$line_id" = "$id" ] && mount="$line"
  done < <(hh_archive_disk_list)
  if [ -z "$mount" ]; then
    hh_archive_disk_say "FEHLER: Platte $id ist nicht in der Liste der erlaubten Platten."
    return 1
  fi
  if [ "$mount" = "/" ]; then target="/srv/hydrahive-archiv"; else target="$mount/hydrahive-archiv"; fi
  hh_archive_disk_say "Richte $target für $owner ein"
  # mkdir ohne -p für das Ziel selbst: legt nichts über einen Symlink hinweg an. Danach nur weiter, wenn es ein
  # echtes Verzeichnis ist (kein Symlink) – chown/chmod wirken dann garantiert auf genau diesen Ordner.
  [ "$mount" = "/" ] && { mkdir -p -- /srv || return 1; }
  [ -e "$target" ] || [ -L "$target" ] || mkdir -- "$target" || return 1
  if [ -L "$target" ] || [ ! -d "$target" ]; then
    hh_archive_disk_say "FEHLER: $target ist ein Symlink oder kein Ordner – wird nicht angefasst."
    return 1
  fi
  chown -h -- "$owner:$owner" "$target" || return 1
  chmod 2775 -- "$target" || return 1
  return 0
}
