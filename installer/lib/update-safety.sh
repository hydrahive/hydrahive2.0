#!/usr/bin/env bash
# Sicherung vor dem Update (docs/specs/update-rollback.md §3.1 Phase A, §6 Aufbewahrung, Etappe U3).
#
# Wird von update.sh gesourct und läuft als root. Noch KEIN automatischer Rückweg (U4): hier entsteht nur die
# Sicherung samt Anleitung für einen Rückweg von Hand.
#
# Ordner je Lauf:  /var/backups/hydrahive2/update/<UTC>_<alter-commit-kurz>/   (root:root, 0700)
#   Bewusst NICHT unter $HH_DATA_DIR (gehört dem Dienstnutzer): dort könnte er per Symlink root-Schreibzugriffe umlenken.
#   meta.env            KEY=Wert (siehe hh_meta_set)        sessions.db.zst  VACUUM INTO + quick_check + zstd (ohne zstd: .gz)
#   etc-hydrahive2.tar  Konfiguration (0600)                 units/           Unit, nginx-Site, sudoers
#   dist/               frontend/dist                        modules-frontend/ frontend/src/modules
#   venv.tar.zst        nur bei geändertem Python/pyproject  update-safety.sh, db_snapshot.py (Kopie, §4 Grundsatz)
#   ROLLBACK.txt        Rückweg von Hand
#
# Erwartet aus update.sh: log, err, HH_REPO_DIR, HH_USER, HH_DATA_DIR, HH_CONFIG_DIR (und für Schritt 2 HH_GIT).
# Bash-3.2-tauglich ist das hier nicht nötig (nur Linux), aber ohne Bash-4-Besonderheiten geschrieben.

HH_SAFETY_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

hh_backup_root() { printf '%s\n' "${HH_BACKUP_ROOT:-/var/backups/hydrahive2/update}"; }

# Endung der Kompression: zstd, sonst gzip (zstd ist nicht überall installiert; das Update darf daran nicht scheitern).
hh_zext() { if command -v zstd >/dev/null 2>&1; then echo zst; else echo gz; fi; }

# Ein Verzeichnis, in das root schreibt, muss echt, root-eigen (hier: Besitzer = aufrufender Nutzer) und für Gruppe/Andere
# nicht schreibbar sein – sonst könnte der Dienstnutzer es austauschen und root-Schreibzugriffe umlenken.
hh_assert_private_dir() {
  local d=$1 owner mode
  [ -d "$d" ] && [ ! -L "$d" ] || err "Sicherungsordner $d ist kein echtes Verzeichnis – nichts verändert."
  owner="$(stat -c %u "$d" 2>/dev/null)"; mode="$(stat -c %a "$d" 2>/dev/null)"
  [ "$owner" = "$EUID" ] || err "Sicherungsordner $d gehört nicht root (Besitzer $owner) – nichts verändert."
  case "$mode" in *[2367]?|*[2367]) err "Sicherungsordner $d ist für andere schreibbar ($mode) – nichts verändert." ;; esac
}

# ---------------------------------------------------------------------------------------------------------------
# Hilfen
# ---------------------------------------------------------------------------------------------------------------

hh_free_bytes() { df -PB1 "$1" 2>/dev/null | awk 'NR==2 {print $4}'; }

hh_fs_id() { stat -c %d "$1" 2>/dev/null; }

hh_dir_bytes() { local n=0; [ -e "$1" ] && n=$(du -sb "$1" 2>/dev/null | awk '{print $1}'); echo "${n:-0}"; }

hh_gb() { awk -v n="${1:-0}" 'BEGIN { printf "%.1f", n / 1073741824 }'; }

# Fest: root führt das aus, und install.conf (vom Dienstnutzer beschreibbar) darf den Interpreter nicht bestimmen.
# Tests setzen HH_TEST_SYSTEM_PYTHON ausdrücklich (nur bei gesetztem HH_TEST_MODE).
hh_safety_python() {
  if [ "${HH_TEST_MODE:-}" = "1" ] && [ -n "${HH_TEST_SYSTEM_PYTHON:-}" ]; then printf '%s\n' "$HH_TEST_SYSTEM_PYTHON"; else printf '%s\n' /usr/bin/python3; fi
}

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

hh_meta_set_in() {   # <ordner> KEY WERT
  local saved="${HH_BACKUP_DIR:-}"
  HH_BACKUP_DIR="$1"; hh_meta_set "$2" "$3"; HH_BACKUP_DIR="$saved"
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
  # Der Sicherungsordner existiert noch nicht (es wird vor der Prüfung nichts angelegt): den nächsten vorhandenen Elternordner messen.
  while [ ! -d "$root" ] && [ "$root" != "/" ]; do root="$(dirname "$root")"; done
  for path in "$root" "$(dirname "$db")"; do
    free=$(hh_free_bytes "$path")
    [ -n "$free" ] || err "Freien Platz auf $path nicht ermittelbar – nichts verändert."
    if [ "$free" -lt "$need" ]; then
      err "Zu wenig Platz für die Sicherung: frei $(hh_gb "$free") GB, nötig $(hh_gb "$need") GB – nichts verändert"
    fi
  done
}

hh_backup_make_dir() {   # <alter-commit>
  local root stamp short parent
  root=$(hh_backup_root)
  parent="$(dirname "$root")"
  ( umask 077; mkdir -p "$parent" "$root" ) || err "Sicherungsordner $root nicht anlegbar – nichts verändert."
  hh_assert_private_dir "$parent"
  hh_assert_private_dir "$root"
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  short="${1:0:8}"
  HH_BACKUP_DIR="$root/${stamp}_${short}"
  ( umask 077; mkdir "$HH_BACKUP_DIR" ) || err "Sicherungsordner $HH_BACKUP_DIR nicht anlegbar – nichts verändert."
  export HH_BACKUP_DIR
}

hh_backup_db() {   # <db> <ziel.zst|.gz>
  local db=$1 dest=$2 py work raw out
  py=$(hh_safety_python)
  # Die Kopie läuft als Besitzer der DB (root würde bei gestopptem Dienst -wal/-shm root-eigen anlegen). Das
  # Arbeitsverzeichnis legt deshalb auch der DB-Besitzer an: root führt auf Pfaden des Dienstnutzers kein chown/chmod aus.
  work=$(hh_as_dbowner mktemp -d "$HH_DATA_DIR/.update-work.XXXXXX") \
    || err "Arbeitsordner für die DB-Sicherung nicht anlegbar – nichts verändert"
  raw="$work/update.db"
  out=$(hh_as_dbowner_lowprio "$py" "$HH_SAFETY_LIB_DIR/db_snapshot.py" copy "$db" "$raw" 2>&1) \
    || { hh_as_dbowner rm -rf "$work"; err "DB-Sicherung fehlgeschlagen ($out) – nichts verändert"; }
  out=$(hh_lowprio "$py" "$HH_SAFETY_LIB_DIR/db_snapshot.py" pack "$raw" "$dest" 2>&1) \
    || { hh_as_dbowner rm -rf "$work"; rm -f "$dest"; err "DB-Sicherung fehlgeschlagen ($out) – nichts verändert"; }
  hh_as_dbowner rm -rf "$work"
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
    # Echte Kopie, keine Hardlinks: Die Sicherung teilt sonst Inodes mit dem Live-Baum, und jedes Schreiben in eine
    # vorhandene Datei (oder ein kompromittierter Dienstnutzer) würde auch die Sicherung ändern. Kosten auf .4: rund 1 s, 100 MB.
    cp -a "$HH_REPO_DIR/frontend/dist" "$dir/dist" || err "Sicherung von frontend/dist fehlgeschlagen – nichts verändert"
  fi
  if [ -d "$HH_REPO_DIR/frontend/src/modules" ]; then
    cp -a "$HH_REPO_DIR/frontend/src/modules" "$dir/modules-frontend" \
      || err "Sicherung von frontend/src/modules fehlgeschlagen – nichts verändert"
  fi
  if [ "$1" = "1" ]; then
    if [ "$(hh_zext)" = zst ]; then
      ( set -o pipefail; tar -C "$HH_REPO_DIR" -cf - .venv | zstd -3 -T0 -q -o "$dir/venv.tar.zst" ) \
        || err "Sicherung des Python-venv fehlgeschlagen – nichts verändert"
    else
      ( set -o pipefail; tar -C "$HH_REPO_DIR" -czf "$dir/venv.tar.gz" .venv ) \
        || err "Sicherung des Python-venv fehlgeschlagen – nichts verändert"
    fi
  fi
}

hh_backup_write_guide() {
  local dir=$HH_BACKUP_DIR old=$1 db="$HH_DATA_DIR/sessions.db" ext unz venvcmd
  ext="$(hh_zext)"
  if [ "$ext" = zst ]; then unz="zstd -d -o $db $dir/sessions.db.zst"; venvcmd="zstd -dc $dir/venv.tar.zst | tar -C $HH_REPO_DIR -xf -"
  else unz="gzip -dc $dir/sessions.db.gz > $db"; venvcmd="tar -C $HH_REPO_DIR -xzf $dir/venv.tar.gz"; fi
  cat > "$dir/ROLLBACK.txt" <<EOF
Rückweg von Hand (automatischer Rückweg folgt mit Etappe U4)
Sicherung: $dir
Alter Commit: $old

1. systemctl stop hydrahive2.service
2. Kaputten Stand NICHT löschen, zur Seite legen:
     mkdir -p $dir/kaputt && mv $db $db-wal $db-shm $dir/kaputt/ 2>/dev/null
3. Datenbank zurückspielen:
     $unz && chown $HH_USER:$HH_USER $db
4. Code zurück:
     sudo -u $HH_USER git -C $HH_REPO_DIR reset --hard $old
5. Frontend zurück (kein Neubau nötig):
     rm -rf $HH_REPO_DIR/frontend/dist && cp -a $dir/dist $HH_REPO_DIR/frontend/dist
     rm -rf $HH_REPO_DIR/frontend/src/modules && cp -a $dir/modules-frontend $HH_REPO_DIR/frontend/src/modules
6. Konfiguration (nur bei Bedarf):
     tar -C $(dirname "$HH_CONFIG_DIR") -xf $dir/etc-hydrahive2.tar
     Units: cp -a $dir/units/* an die ursprünglichen Orte, danach systemctl daemon-reload
7. venv (nur wenn $dir/venv.tar.$ext existiert):
     rm -rf $HH_REPO_DIR/.venv && $venvcmd
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
  old="$($HH_GIT rev-parse -q --verify HEAD 2>/dev/null || true)"
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
  local f
  # §4 Grundsatz: Prüfung und Rückweg laufen aus DIESER Kopie, nicht aus dem (evtl. kaputten) neuen Stand.
  for f in update-safety.sh update-check.sh update-rollback.sh db_snapshot.py; do
    [ -f "$HH_SAFETY_LIB_DIR/$f" ] || continue
    cp --no-preserve=ownership,mode "$HH_SAFETY_LIB_DIR/$f" "$HH_BACKUP_DIR/$f" 2>/dev/null && chmod 600 "$HH_BACKUP_DIR/$f" || true
  done

  if [ -f "$db" ]; then
    log "Datenbank sichern (VACUUM INTO, geprüft)"
    hh_backup_db "$db" "$HH_BACKUP_DIR/sessions.db.$(hh_zext)"
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

# Hat das Update schon etwas verändert? Entscheidend ist der ZUSTAND, nicht eine Shell-Variable: Nach einem Re-exec
# ist HH_PHASE_B leer, der Code aber schon neu (Review #760, Fund 1). Im Zweifel: ja (Sicherung behalten).
hh_safety_changed() {
  local old head
  [ -n "${HH_PHASE_B:-}" ] && return 0
  [ -n "${HH_UPDATE_REEXECED:-}" ] && return 0
  old="$(hh_meta_get OLD_COMMIT "$HH_BACKUP_DIR")"
  head="$($HH_GIT rev-parse HEAD 2>/dev/null || true)"
  [ -n "$head" ] && [ -n "$old" ] && [ "$old" != "unbekannt" ] && [ "$head" = "$old" ] && return 1
  return 0
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
  if [ "$status" = "ok" ]; then
    # Phase C hat bestanden und die Sicherung schon als ok markiert; hier bleibt nur das Aufräumen (§6).
    [ "$rc" -eq 0 ] && hh_backup_prune || true
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
  elif ! hh_safety_changed; then
    # Git-Schritt abgelehnt o. Ä.: es wurde nichts verändert, die Sicherung wird nicht gebraucht.
    rm -rf --one-file-system -- "$HH_BACKUP_DIR"
    log "Nichts verändert."
  else
    hh_safety_rollback "$rc"
  fi
  return 0
}

# Phase D aus dem trap: nach einem Fehler ab Phase B automatisch zurück (HH_UPDATE_ROLLBACK=0 schaltet es ab).
# Setzt HH_FAIL_REASON auf die Schlusszeile („… – auf <alt> zurückgesetzt“) und STATUS in meta.env.
hh_safety_rollback() {
  local rc=$1 dir=$HH_BACKUP_DIR reason f
  reason="${HH_FAIL_REASON:-Abbruch (Code $rc) – siehe Log}"
  if [ "${HH_UPDATE_ROLLBACK:-1}" = "0" ]; then
    log "Update fehlgeschlagen. Automatischer Rückweg abgeschaltet (HH_UPDATE_ROLLBACK=0). Sicherung: $dir"
    log "Rückweg von Hand: cat $dir/ROLLBACK.txt"
    return 0
  fi
  # Prüfung und Rückweg aus der Kopie im Sicherungsordner (§4 Grundsatz); fehlt sie, aus dem Repo.
  for f in update-check.sh update-rollback.sh; do
    if [ -f "$dir/$f" ]; then source "$dir/$f"; elif [ -f "$HH_SAFETY_LIB_DIR/$f" ]; then source "$HH_SAFETY_LIB_DIR/$f"; fi
  done
  if ! declare -F hh_rollback_run >/dev/null 2>&1; then
    log "Rückweg-Code nicht gefunden. Rückweg von Hand: cat $dir/ROLLBACK.txt"
    return 0
  fi
  hh_rollback_run "$dir" "$reason" || true
  case "$HH_ROLLBACK_STATE" in
    ok)             hh_meta_set STATUS zurueckgesetzt ;;
    unvollstaendig) hh_meta_set STATUS rueckweg_unvollstaendig
                    log "Rückweg unvollständig. Rest von Hand: cat $dir/ROLLBACK.txt (kaputter Stand: $dir/kaputt/)" ;;
    unmoeglich)     hh_meta_set STATUS rueckweg_unvollstaendig
                    log "Rückweg nicht möglich. Sicherung: $dir (ROLLBACK.txt)" ;;
    *)              log "Rückweg ohne Ergebnis. Sicherung: $dir (ROLLBACK.txt)"; return 0 ;;
  esac
  HH_FAIL_REASON="$HH_ROLLBACK_MESSAGE"
  return 0
}

# E13: Ein früheres Update wurde hart beendet (Stromausfall, kill -9): Sicherung mit STATUS=gesichert ohne Abschluss.
# Wir halten die Sperre, es läuft also kein anderes. Nur MELDEN (F6); automatisch zurück nur, wenn der Dienst mit dem
# neuen Stand nicht startet.
hh_safety_check_interrupted() {
  local root d name st old new head
  root=$(hh_backup_root)
  [ -d "$root" ] || return 0
  while IFS= read -r name; do
    d="$root/$name"
    [ -d "$d" ] && [ ! -L "$d" ] || continue
    [ "${d}" = "${HH_BACKUP_DIR:-}" ] && continue
    st="$(hh_meta_get STATUS "$d")"
    [ "$st" = "gesichert" ] || continue
    old="$(hh_meta_get OLD_COMMIT "$d")"; new="$(hh_meta_get NEW_COMMIT "$d")"
    hh_meta_set_in "$d" STATUS unterbrochen
    log "WARNUNG: Vorheriges Update unterbrochen – Sicherung $d (alter Commit ${old:0:8}). Rückweg von Hand: cat $d/ROLLBACK.txt"
    if declare -F hh_warn >/dev/null 2>&1; then hh_warn "Vorheriges Update unterbrochen – Sicherung $d"; fi
    head="$($HH_GIT rev-parse HEAD 2>/dev/null || true)"
    # Automatisch nur, wenn der Dienst mit dem neuen Stand nicht läuft (F6).
    if [ -n "$new" ] && [ "$head" = "$new" ] && [ "$(hh_meta_get RESTARTED "$d")" = "1" ] \
       && declare -F hh_safety_verify >/dev/null 2>&1; then
      HH_UPDATE_HEALTH_TIMEOUT="${HH_INTERRUPTED_HEALTH_TIMEOUT:-20}" hh_safety_verify "$new" 1 || {
        log "Der Dienst läuft mit dem Stand des unterbrochenen Updates nicht ($HH_VERIFY_REASON) – automatischer Rückweg"
        hh_safety_rollback_dir "$d"
      }
    fi
  done < <(ls -1 "$root" 2>/dev/null | grep -E '^[0-9]{8}T[0-9]{6}Z_[0-9a-f]+$|^[0-9]{8}T[0-9]{6}Z_unbekannt$' | sort)
  return 0
}

hh_safety_rollback_dir() {
  local d=$1 saved_dir="${HH_BACKUP_DIR:-}" saved_reason="${HH_FAIL_REASON:-}"
  HH_BACKUP_DIR="$d"; HH_FAIL_REASON="Vorheriges Update unterbrochen"
  hh_safety_rollback 1
  HH_BACKUP_DIR="$saved_dir"; HH_FAIL_REASON="$saved_reason"
  return 0
}
