#!/usr/bin/env bash
# Sicherung vor dem Update (docs/specs/update-rollback.md §3.1 Phase A, §6 Aufbewahrung, Etappe U3).
#
# Wird von update.sh gesourct und läuft als root. Noch KEIN automatischer Rückweg (U4): hier entsteht nur die
# Sicherung samt Anleitung für einen Rückweg von Hand.
#
# Ordner je Lauf:  $HH_DATA_DIR/backups/update/<UTC>_<alter-commit-kurz>/   (root:root, 0700)
#   meta.env            KEY=Wert (siehe hh_meta_set)        sessions.db.zst  VACUUM INTO + quick_check + zstd
#   etc-hydrahive2.tar  Konfiguration (0600)                 units/           Unit, nginx-Site, sudoers
#   dist/               frontend/dist                        modules-frontend/ frontend/src/modules
#   venv.tar.zst        nur bei geändertem Python/pyproject  update-safety.sh, db_snapshot.py (Kopie, §4 Grundsatz)
#   ROLLBACK.txt        Rückweg von Hand
#
# Erwartet aus update.sh: log, err, HH_REPO_DIR, HH_USER, HH_DATA_DIR, HH_CONFIG_DIR (und für Schritt 2 HH_GIT).
# Bash-3.2-tauglich ist das hier nicht nötig (nur Linux), aber ohne Bash-4-Besonderheiten geschrieben.

HH_BACKUP_ROOT_DEFAULT_SUBDIR="backups/update"
HH_SAFETY_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

hh_backup_root() { printf '%s\n' "${HH_BACKUP_ROOT:-$HH_DATA_DIR/$HH_BACKUP_ROOT_DEFAULT_SUBDIR}"; }

# ---------------------------------------------------------------------------------------------------------------
# Hilfen
# ---------------------------------------------------------------------------------------------------------------

hh_free_bytes() { df -PB1 "$1" 2>/dev/null | awk 'NR==2 {print $4}'; }

hh_fs_id() { stat -c %d "$1" 2>/dev/null; }

hh_dir_bytes() { local n=0; [ -e "$1" ] && n=$(du -sb "$1" 2>/dev/null | awk '{print $1}'); echo "${n:-0}"; }

hh_gb() { awk -v n="${1:-0}" 'BEGIN { printf "%.1f", n / 1073741824 }'; }

hh_safety_python() { printf '%s\n' "${HH_SYSTEM_PYTHON:-/usr/bin/python3}"; }

# Niedrige Priorität für die Sicherung (Dienst läuft weiter). Fehlt ionice/nice, läuft sie ohne.
hh_lowprio() {
  if command -v ionice >/dev/null 2>&1 && command -v nice >/dev/null 2>&1; then
    ionice -c3 nice -n 19 "$@"
  else
    "$@"
  fi
}

# Zugriffe auf sessions.db als Besitzer der DB, nie als root: Öffnet root eine WAL-DB bei gestopptem Dienst, legt er
# -wal und -shm root-eigen an, und der Dienst startet danach nicht mehr.
hh_as_dbowner() {
  if [ "$(id -u)" -eq 0 ] && [ "$HH_USER" != "root" ]; then
    sudo -u "$HH_USER" "$@"
  else
    "$@"
  fi
}

# Wie hh_as_dbowner, aber mit niedriger I/O- und CPU-Priorität (ionice kann keine Shell-Funktion starten).
hh_as_dbowner_lowprio() {
  if command -v ionice >/dev/null 2>&1 && command -v nice >/dev/null 2>&1; then
    hh_as_dbowner ionice -c3 nice -n 19 "$@"
  else
    hh_as_dbowner "$@"
  fi
}

# meta.env atomar fortschreiben: hh_meta_set KEY WERT (Werte ohne Leerzeichen und Zeilenumbruch).
hh_meta_set() {
  local key=$1 value=$2 file="${HH_BACKUP_DIR:-}/meta.env" tmp
  [ -n "${HH_BACKUP_DIR:-}" ] && [ -d "$HH_BACKUP_DIR" ] || return 0
  value="${value//[$'\n\r ']/_}"
  tmp="$file.tmp"
  { [ -f "$file" ] && grep -v "^${key}=" "$file" || true; printf '%s=%s\n' "$key" "$value"; } > "$tmp" \
    && chmod 600 "$tmp" && mv "$tmp" "$file"
}

hh_meta_get() { [ -f "$2/meta.env" ] && sed -n "s/^$1=//p" "$2/meta.env" | tail -1; }

# ---------------------------------------------------------------------------------------------------------------
# Schritt 1: Sperre
# ---------------------------------------------------------------------------------------------------------------

# Genau ein Update gleichzeitig. Der Re-exec (HH_UPDATE_REEXECED) erbt den offenen Deskriptor 9 samt Sperre.
hh_safety_lock() {
  local lock="${HH_UPDATE_LOCK:-/run/hydrahive2-update.lock}"
  [ -n "${HH_UPDATE_REEXECED:-}" ] && [ -n "${HH_UPDATE_LOCK_HELD:-}" ] && return 0
  command -v flock >/dev/null 2>&1 || err "flock fehlt (util-linux) – Update angehalten, nichts verändert."
  exec 9> "$lock" || err "Sperrdatei $lock nicht beschreibbar – nichts verändert."
  flock -n 9 || err "Update läuft bereits – nichts verändert."
  export HH_UPDATE_LOCK_HELD=1
}

# ---------------------------------------------------------------------------------------------------------------
# Schritt 2–6: Sicherung
# ---------------------------------------------------------------------------------------------------------------

# Muss die venv gesichert werden (F3)? Ja, wenn der Interpreter wechselt (hh_venv_needs_rebuild) oder sich
# core/pyproject.toml zwischen altem Stand und origin/<Branch> ändert. Im Zweifel: ja.
hh_backup_wants_venv() {
  local old=$1 branch=$2 py
  [ -x "$HH_REPO_DIR/.venv/bin/python" ] || return 1
  [ "$old" = "unbekannt" ] && return 0
  # shellcheck source=python-venv.sh
  source "$HH_REPO_DIR/installer/lib/python-venv.sh" 2>/dev/null || return 0
  py="$(hh_pick_python 2>/dev/null)" || return 0
  hh_venv_needs_rebuild "$HH_REPO_DIR/.venv" "$py" && return 0
  [ -n "$branch" ] || return 0
  if $HH_GIT cat-file -e "origin/$branch" 2>/dev/null; then
    $HH_GIT diff --quiet "$old" "origin/$branch" -- core/pyproject.toml 2>/dev/null && return 1
  fi
  return 0
}

hh_backup_need_bytes() {   # <db-nutzdaten> <venv-bytes>
  local est=$1 venv=$2 dist mods
  dist=$(hh_dir_bytes "$HH_REPO_DIR/frontend/dist")
  mods=$(hh_dir_bytes "$HH_REPO_DIR/frontend/src/modules")
  awk -v e="$est" -v d="$dist" -v m="$mods" -v v="$venv" 'BEGIN { printf "%d", e * 1.2 + d + m + v + 1073741824 }'
}

# Platz prüfen: auf dem Dateisystem des Sicherungsordners UND dem von sessions.db (WAL, VACUUM-Zwischendatei).
hh_backup_check_space() {   # <need> <backup-root> <db>
  local need=$1 root=$2 db=$3 free path
  for path in "$root" "$(dirname "$db")"; do
    free=$(hh_free_bytes "$path")
    [ -n "$free" ] || err "Freien Platz auf $path nicht ermittelbar – nichts verändert."
    if [ "$free" -lt "$need" ]; then
      err "Zu wenig Platz für die Sicherung: frei $(hh_gb "$free") GB, nötig $(hh_gb "$need") GB – nichts verändert"
    fi
  done
}

hh_backup_make_dir() {   # <alter-commit>
  local root stamp short
  root=$(hh_backup_root)
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  short="${1:0:8}"
  HH_BACKUP_DIR="$root/${stamp}_${short}"
  ( umask 077; mkdir -p "$root" "$HH_BACKUP_DIR" ) || err "Sicherungsordner $HH_BACKUP_DIR nicht anlegbar – nichts verändert."
  chmod 700 "$root" "$HH_BACKUP_DIR"
  export HH_BACKUP_DIR
}

hh_backup_db() {   # <db> <ziel.zst>
  local db=$1 dest=$2 py work raw out
  py=$(hh_safety_python)
  # Die Kopie läuft als Besitzer der DB: root würde bei gestopptem Dienst -wal/-shm root-eigen anlegen.
  work="$(dirname "$(hh_backup_root)")/.work"
  ( umask 077; mkdir -p "$work" ) || return 1
  [ "$(id -u)" -eq 0 ] && chown "$HH_USER:$HH_USER" "$work" 2>/dev/null
  chmod 700 "$work"
  chmod 711 "$(dirname "$(hh_backup_root)")" 2>/dev/null
  raw="$work/update-$$.db"
  out=$(hh_as_dbowner_lowprio "$py" "$HH_SAFETY_LIB_DIR/db_snapshot.py" copy "$db" "$raw" 2>&1) \
    || { rm -f "$raw"; err "DB-Sicherung fehlgeschlagen ($out) – nichts verändert"; }
  out=$(hh_lowprio "$py" "$HH_SAFETY_LIB_DIR/db_snapshot.py" pack "$raw" "$dest" 2>&1) \
    || { rm -f "$raw" "$dest"; err "DB-Sicherung fehlgeschlagen ($out) – nichts verändert"; }
  out=$("$py" "$HH_SAFETY_LIB_DIR/db_snapshot.py" verify "$dest" 2>&1) \
    || { rm -f "$dest"; err "DB-Sicherung nicht lesbar ($out) – nichts verändert"; }
  hh_meta_set DB_BACKUP_BYTES "$(stat -c %s "$dest")"
}

hh_backup_files() {   # <venv:0|1>
  local dir=$HH_BACKUP_DIR cfg_parent cfg_name f
  ( umask 077
    cfg_parent="$(dirname "$HH_CONFIG_DIR")"; cfg_name="$(basename "$HH_CONFIG_DIR")"
    if [ -d "$HH_CONFIG_DIR" ]; then
      tar -C "$cfg_parent" -cf "$dir/etc-hydrahive2.tar" "$cfg_name" || exit 1
      chmod 600 "$dir/etc-hydrahive2.tar"
    fi
    mkdir -p "$dir/units"
    for f in "${HH_UNIT_FILE:-/etc/systemd/system/hydrahive2.service}" \
             "${HH_NGINX_SITE:-/etc/nginx/sites-available/hydrahive2}" \
             "${HH_SUDOERS_FILE:-/etc/sudoers.d/hydrahive2-extensions}"; do
      if [ -e "$f" ]; then cp -a "$f" "$dir/units/" || exit 1; fi
    done
    f="${HH_UNIT_FILE:-/etc/systemd/system/hydrahive2.service}.d"
    if [ -d "$f" ]; then cp -a "$f" "$dir/units/" || exit 1; fi
    exit 0
  ) || err "Sicherung der Konfiguration fehlgeschlagen – nichts verändert"
  if [ -d "$HH_REPO_DIR/frontend/dist" ]; then
    # Hardlinks (gleiches Dateisystem) sind ok: Bau und Tausch schreiben nie in vorhandene Dateien (U2).
    cp -al "$HH_REPO_DIR/frontend/dist" "$dir/dist" 2>/dev/null || { rm -rf "$dir/dist"; cp -a "$HH_REPO_DIR/frontend/dist" "$dir/dist"; } \
      || err "Sicherung von frontend/dist fehlgeschlagen – nichts verändert"
  fi
  if [ -d "$HH_REPO_DIR/frontend/src/modules" ]; then
    cp -a "$HH_REPO_DIR/frontend/src/modules" "$dir/modules-frontend" \
      || err "Sicherung von frontend/src/modules fehlgeschlagen – nichts verändert"
  fi
  if [ "$1" = "1" ]; then
    ( set -o pipefail; tar -C "$HH_REPO_DIR" -cf - .venv | zstd -3 -T0 -q -o "$dir/venv.tar.zst" ) \
      || err "Sicherung des Python-venv fehlgeschlagen – nichts verändert"
  fi
}

hh_backup_write_guide() {
  local dir=$HH_BACKUP_DIR old=$1 db="$HH_DATA_DIR/sessions.db"
  cat > "$dir/ROLLBACK.txt" <<EOF
Rückweg von Hand (automatischer Rückweg folgt mit Etappe U4)
Sicherung: $dir
Alter Commit: $old

1. systemctl stop hydrahive2.service
2. Kaputten Stand NICHT löschen, zur Seite legen:
     mkdir -p $dir/kaputt && mv $db $db-wal $db-shm $dir/kaputt/ 2>/dev/null
3. Datenbank zurückspielen:
     zstd -d -o $db $dir/sessions.db.zst && chown $HH_USER:$HH_USER $db
4. Code zurück:
     sudo -u $HH_USER git -C $HH_REPO_DIR reset --hard $old
5. Frontend zurück (kein Neubau nötig):
     rm -rf $HH_REPO_DIR/frontend/dist && cp -a $dir/dist $HH_REPO_DIR/frontend/dist
     rm -rf $HH_REPO_DIR/frontend/src/modules && cp -a $dir/modules-frontend $HH_REPO_DIR/frontend/src/modules
6. Konfiguration (nur bei Bedarf):
     tar -C $(dirname "$HH_CONFIG_DIR") -xf $dir/etc-hydrahive2.tar
     Units: cp -a $dir/units/* an die ursprünglichen Orte, danach systemctl daemon-reload
7. venv (nur wenn $dir/venv.tar.zst existiert):
     rm -rf $HH_REPO_DIR/.venv && zstd -dc $dir/venv.tar.zst | tar -C $HH_REPO_DIR -xf -
     sonst: sudo -u $HH_USER $HH_REPO_DIR/.venv/bin/pip install -e $HH_REPO_DIR/core
8. systemctl start hydrahive2.service; curl -fsS http://127.0.0.1:8001/api/health
EOF
  chmod 600 "$dir/ROLLBACK.txt"
}

# Phase A. Setzt HH_BACKUP_DIR und HH_OLD_COMMIT (beides exportiert, damit ein Re-exec nichts doppelt sichert).
hh_safety_backup() {
  local old branch db est venv_bytes=0 want_venv=0 need root
  if [ -n "${HH_BACKUP_DIR:-}" ] && [ -f "$HH_BACKUP_DIR/meta.env" ]; then
    log "Sicherung aus dem ersten Lauf bleibt gültig: $HH_BACKUP_DIR (keine zweite)"
    return 0
  fi
  root=$(hh_backup_root)
  db="$HH_DATA_DIR/sessions.db"
  branch="${HH_GIT_BRANCH:-}"
  old="$($HH_GIT rev-parse HEAD 2>/dev/null || true)"
  [ -n "$old" ] || err "Aktueller Commit nicht ermittelbar – nichts verändert."
  if [ -n "${HH_UPDATE_REEXECED:-}" ]; then
    # Ein älteres update.sh hat schon gepullt und uns neu gestartet: HEAD ist der NEUE Stand.
    old="$($HH_GIT rev-parse -q --verify ORIG_HEAD 2>/dev/null || true)"
    [ -n "$old" ] || old="unbekannt"
    log "WARNUNG: Der Pull lief schon vor dieser Sicherung (älteres update.sh). Alter Commit: ${old:0:8}"
  fi

  log "Sicherung vor dem Update"
  if hh_backup_wants_venv "$old" "$branch"; then
    want_venv=1
    venv_bytes=$(hh_dir_bytes "$HH_REPO_DIR/.venv")
  fi
  est=0
  if [ -f "$db" ]; then
    est=$(hh_as_dbowner "$(hh_safety_python)" "$HH_SAFETY_LIB_DIR/db_snapshot.py" estimate "$db" 2>&1) \
      || err "DB-Größe nicht ermittelbar ($est) – nichts verändert"
  fi
  need=$(hh_backup_need_bytes "$est" "$venv_bytes")
  mkdir -p "$root" 2>/dev/null || true
  hh_backup_check_space "$need" "$root" "${db}"

  hh_backup_make_dir "$old"
  export HH_OLD_COMMIT="$old"
  {
    printf 'SCHEMA=1\nSTATUS=anlegen\nSTART=%s\n' "$(date -u +%Y%m%dT%H%M%SZ)"
    printf 'OLD_COMMIT=%s\nOLD_BRANCH=%s\nNEW_COMMIT=\n' "$old" "${branch:-unbekannt}"
    printf 'VENV_BACKED_UP=%s\nDB_BACKED_UP=%s\nNEED_BYTES=%s\n' "$want_venv" "$([ -f "$db" ] && echo 1 || echo 0)" "$need"
  } > "$HH_BACKUP_DIR/meta.env"
  chmod 600 "$HH_BACKUP_DIR/meta.env"

  # §4 Grundsatz: Sicherungs- und (später) Rückweg-Code liegt als Kopie im Ordner, nicht im Repo.
  cp -a "$HH_SAFETY_LIB_DIR/update-safety.sh" "$HH_SAFETY_LIB_DIR/db_snapshot.py" "$HH_BACKUP_DIR/" 2>/dev/null || true

  if [ -f "$db" ]; then
    log "Datenbank sichern (VACUUM INTO, geprüft)"
    hh_backup_db "$db" "$HH_BACKUP_DIR/sessions.db.zst"
  else
    log "Keine sessions.db unter $HH_DATA_DIR – DB-Sicherung entfällt"
  fi
  hh_backup_files "$want_venv"
  hh_backup_write_guide "$old"
  hh_meta_set STATUS gesichert
  log "Sicherung fertig: $HH_BACKUP_DIR (alter Commit ${old:0:8}, venv gesichert: $([ "$want_venv" = 1 ] && echo ja || echo nein))"
  log "Rückweg von Hand: $HH_BACKUP_DIR/ROLLBACK.txt"
}

# Nach hh_git_update: neuen Commit notieren und merken, dass die eigentliche Änderung begonnen hat.
hh_safety_after_git() {
  HH_PHASE_B=1
  hh_meta_set NEW_COMMIT "$($HH_GIT rev-parse HEAD 2>/dev/null || echo unbekannt)"
}

# ---------------------------------------------------------------------------------------------------------------
# Aufbewahrung (§6) und Abschluss
# ---------------------------------------------------------------------------------------------------------------

# Behält die letzten HH_BACKUP_KEEP (2) Sicherungen mit STATUS=ok. NIE gelöscht: gesichert (unterbrochen), zurueckgesetzt, rueckweg_unvollstaendig, alles mit kaputt/.
hh_backup_prune() {
  local root keep=${HH_BACKUP_KEEP:-2} n=0 d name st
  root=$(hh_backup_root)
  [ -d "$root" ] || return 0
  # Namen sortiert, neueste zuerst (UTC-Zeit im Namen)
  while IFS= read -r name; do
    d="$root/$name"
    [ -d "$d" ] && [ ! -L "$d" ] || continue
    [ -d "$d/kaputt" ] && continue
    st="$(hh_meta_get STATUS "$d")"
    case "$st" in
      ok)
        n=$((n + 1))
        if [ "$n" -gt "$keep" ]; then log "Alte Sicherung entfernt: $name"; rm -rf --one-file-system -- "$d"; fi ;;
    esac
  done < <(ls -1 "$root" 2>/dev/null | grep -E '^[0-9]{8}T[0-9]{6}Z_[0-9a-f]+$|^[0-9]{8}T[0-9]{6}Z_unbekannt$' | sort -r)
}

# Aus dem trap von update.sh, VOR der Schlusszeile. Verändert den Exit-Code nie.
hh_safety_finish() {
  local rc=$1 new old status
  [ -n "${HH_BACKUP_DIR:-}" ] && [ -f "$HH_BACKUP_DIR/meta.env" ] || return 0
  status="$(hh_meta_get STATUS "$HH_BACKUP_DIR")"
  if [ "$status" = "anlegen" ]; then
    # Die Sicherung selbst ist gescheitert (Platte voll, DB gesperrt): halber Ordner, nichts am System verändert.
    [ "$rc" -ne 0 ] && rm -rf --one-file-system -- "$HH_BACKUP_DIR"
    return 0
  fi
  [ "$status" = "gesichert" ] || return 0
  if [ "$rc" -eq 0 ]; then
    new="$($HH_GIT rev-parse HEAD 2>/dev/null || true)"
    old="$(hh_meta_get OLD_COMMIT "$HH_BACKUP_DIR")"
    if [ -n "$new" ] && [ "$new" = "$old" ]; then
      # kein neuer Code: die Sicherung ersetzt keine ältere und zählt nicht zu den „letzten 2“
      rm -rf --one-file-system -- "$HH_BACKUP_DIR"
    else
      hh_meta_set STATUS ok                    # bis U4: Dienst aktiv; Health und Migrationsstand folgen mit Phase C
    fi
    hh_backup_prune || true
  elif [ -z "${HH_PHASE_B:-}" ]; then
    # Git-Schritt abgelehnt o. Ä.: es wurde nichts verändert, die Sicherung wird nicht gebraucht.
    rm -rf --one-file-system -- "$HH_BACKUP_DIR"
    log "Nichts verändert."
  else
    log "Update fehlgeschlagen. Sicherung vom Stand vor dem Update: $HH_BACKUP_DIR"
    log "Rückweg von Hand: cat $HH_BACKUP_DIR/ROLLBACK.txt (automatischer Rückweg folgt mit U4)"
  fi
  return 0
}
