#!/usr/bin/env bash
# Phase C: Prüfung nach dem Neustart (docs/specs/update-rollback.md §3.3, Etappe U4) und Warnungs-Sammlung (E10).
#
# Wird von update.sh gesourct (läuft als root). Erwartet: log, update-safety.sh (hh_meta_*, hh_as_dbowner, hh_safety_python),
# HH_REPO_DIR, HH_DATA_DIR, HH_GIT.
#
# Ein Update gilt erst als erfolgreich, wenn ALLES stimmt:
#   1. Dienst aktiv und keine Neustart-Schleife (NRestarts steigt nicht),
#   2. GET /api/health liefert status "ok" UND den erwarteten Commit,
#   3. die Migrationen sind durchgelaufen (höchste Version in schema_version >= höchste Migrationsdatei des neuen Stands).
# Wartezeit: HH_UPDATE_HEALTH_TIMEOUT (Standard 120 s), Takt HH_UPDATE_HEALTH_INTERVAL (Standard 2 s).

HH_WARNINGS="${HH_WARNINGS:-}"

# ---------------------------------------------------------------------------------------------------------------
# Warnungen (E10): „… — weiter“-Schritte scheitern nicht still, sondern werden am Ende gesammelt ausgegeben.
# Die Sammlung wird exportiert, damit sie einen Re-exec überlebt.
# ---------------------------------------------------------------------------------------------------------------

hh_warn() {
  log "WARNUNG: $*"
  HH_WARNINGS="${HH_WARNINGS}${HH_WARNINGS:+$'\n'}$*"
  export HH_WARNINGS
  return 0
}

hh_print_warnings() {
  local line
  [ -n "${HH_WARNINGS:-}" ] || return 0
  while IFS= read -r line; do
    [ -n "$line" ] && printf 'HH-UPDATE-WARNUNG: %s\n' "$line"
  done <<< "$HH_WARNINGS"
  return 0
}

# ---------------------------------------------------------------------------------------------------------------
# Hilfen
# ---------------------------------------------------------------------------------------------------------------

# Adresse des Dienstes: Port aus der Umgebung (install.conf), sonst aus der Unit, sonst 8001 – nie fest verdrahtet.
hh_health_url() {
  local host="${HH_HOST:-127.0.0.1}" port="${HH_PORT:-}" unit="${HH_UNIT_FILE:-/etc/systemd/system/hydrahive2.service}"
  if [ -z "$port" ] && [ -r "$unit" ]; then
    port="$(sed -n 's/^Environment=HH_PORT=\([0-9]\{1,5\}\)[[:space:]]*$/\1/p' "$unit" | tail -1)"
  fi
  case "$port" in ''|*[!0-9]*) port=8001 ;; esac
  case "$host" in ''|0.0.0.0|::|'[::]') host=127.0.0.1 ;; esac
  printf 'http://%s:%s/api/health\n' "$host" "$port"
}

hh_service_nrestarts() {
  local n
  n="$(systemctl show -p NRestarts --value hydrahive2.service 2>/dev/null | head -1)"
  case "$n" in ''|*[!0-9]*) n=0 ;; esac
  echo "$n"
}

# Höchste Migrationsnummer des CHECKOUTS (Dateien 001_*.sql …), ohne führende Nullen.
hh_expected_migration() {
  local n
  n="$(ls -1 "$HH_REPO_DIR/core/src/hydrahive/db/migrations" 2>/dev/null | sed -n 's/^\([0-9][0-9]*\)_.*\.sql$/\1/p' | sort -n | tail -1)"
  echo "$((10#${n:-0}))"
}

# Eine Health-Abfrage: gibt „<status> <commit>“ aus (leer bei Fehler).
hh_health_probe() {
  local url body
  url="$(hh_health_url)"
  if command -v curl >/dev/null 2>&1; then
    body="$(curl -fsS -m 3 "$url" 2>/dev/null)" || return 1
  else
    body="$("$(hh_safety_python)" -c 'import sys,urllib.request;print(urllib.request.urlopen(sys.argv[1],timeout=3).read().decode())' "$url" 2>/dev/null)" || return 1
  fi
  "$(hh_safety_python)" -c 'import sys,json;d=json.loads(sys.stdin.read());print(d.get("status",""),d.get("commit",""))' <<< "$body" 2>/dev/null
}

# ---------------------------------------------------------------------------------------------------------------
# Phase C
# ---------------------------------------------------------------------------------------------------------------

# hh_safety_verify <erwarteter-commit> [migrationen:1|0]  → 0 = ok. Grund in HH_VERIFY_REASON.
# Migrationsstand als DB-Besitzer lesen. Das Werkzeug kann im Sicherungsordner liegen (root, 0700), den der
# Dienstnutzer nicht lesen darf: root öffnet die Datei und reicht sie per stdin weiter (python3 -).
hh_db_schema_version() {
  local tool=$1 db=$2
  hh_as_dbowner "$(hh_safety_python)" - schema-version "$db" < "$tool"
}

hh_safety_verify() {
  local want=$1 check_mig=${2:-1} timeout interval max i state="" n probe status got base="${HH_NRESTARTS_BASE:-}"
  local tool="${HH_DB_TOOL:-$HH_SAFETY_LIB_DIR/db_snapshot.py}"
  timeout="${HH_UPDATE_HEALTH_TIMEOUT:-120}"; interval="${HH_UPDATE_HEALTH_INTERVAL:-2}"
  case "$timeout" in ''|*[!0-9]*) timeout=120 ;; esac
  max="$(awk -v t="$timeout" -v i="$interval" 'BEGIN { if (i <= 0) i = 2; printf "%d", t / i + 1 }')"
  HH_VERIFY_REASON=""
  for ((i = 1; i <= max; i++)); do
    if ! systemctl is-active --quiet hydrahive2.service 2>/dev/null; then
      state="Dienst nicht aktiv"
    else
      n="$(hh_service_nrestarts)"
      [ -n "$base" ] || base="$n"          # Basis = Stand beim ersten Blick nach dem Neustart
      if [ "$n" -gt "$base" ]; then
        HH_VERIFY_REASON="Dienst startet in einer Schleife neu (NRestarts $n)"
        return 1
      fi
      probe="$(hh_health_probe)" || probe=""
      status="${probe%% *}"; got="${probe#* }"
      if [ -z "$probe" ]; then
        state="/api/health antwortet nicht"
      elif [ "$status" != "ok" ]; then
        state="/api/health meldet Status '$status'"
      elif [ -n "$want" ] && [ "${got:0:7}" != "${want:0:7}" ]; then
        state="/api/health meldet Commit ${got:0:8} statt ${want:0:8}"
      else
        # Eine Neustart-Schleife kann kurz „gesund“ aussehen: nach einer Atempause noch einmal NRestarts lesen.
        sleep "${HH_UPDATE_SETTLE:-1}"
        n="$(hh_service_nrestarts)"
        if [ "$n" -gt "$base" ] || ! systemctl is-active --quiet hydrahive2.service 2>/dev/null; then
          HH_VERIFY_REASON="Dienst startet in einer Schleife neu (NRestarts $n)"
          return 1
        fi
        state=""
        break
      fi
    fi
    sleep "$interval"
  done
  if [ -n "$state" ]; then
    HH_VERIFY_REASON="Health-Prüfung nach ${timeout} s nicht ok ($state)"
    return 1
  fi
  if [ "$check_mig" = "1" ] && [ -f "$HH_DATA_DIR/sessions.db" ]; then
    local have need
    need="$(hh_expected_migration)"
    have="$(hh_db_schema_version "$tool" "$HH_DATA_DIR/sessions.db" 2>/dev/null)" || have=""
    case "$have" in ''|*[!0-9]*) HH_VERIFY_REASON="Migrationsstand nicht lesbar"; return 1 ;; esac
    if [ "$have" -lt "$need" ]; then
      HH_VERIFY_REASON="Migrationen nicht durchgelaufen (DB-Version $have, erwartet $need)"
      return 1
    fi
  fi
  return 0
}

# Vor `systemctl restart`: merken, dass der neue Code gegen die DB laufen darf (Migrationen!).
hh_safety_mark_restart() {
  hh_meta_set RESTARTED 1
  HH_NRESTARTS_BASE=""
}

# Nach bestandener Prüfung: Sicherung zählt als „ok“ (Aufbewahrung §6). Ohne neuen Commit bleibt sie „gesichert“,
# damit hh_safety_finish sie wieder entfernt.
hh_safety_mark_ok() {
  [ -n "${HH_BACKUP_DIR:-}" ] && [ -f "$HH_BACKUP_DIR/meta.env" ] || return 0
  local old head
  old="$(hh_meta_get OLD_COMMIT "$HH_BACKUP_DIR")"
  head="$($HH_GIT rev-parse HEAD 2>/dev/null || true)"
  [ -n "$head" ] && [ "$head" = "$old" ] && return 0
  hh_meta_set STATUS ok
}
