#!/usr/bin/env bash
# Phase D: automatischer Rückweg (docs/specs/update-rollback.md §3.4, Etappe U4).
#
# Wird aus hh_safety_finish (trap von update.sh) aufgerufen, wenn das Update NACH der Sicherung gescheitert ist.
# Grundsätze:
#   - Nie etwas löschen, was Daten sein könnten: der kaputte Stand wird nach kaputt/ gelegt (DB: auf dasselbe
#     Dateisystem wie die DB, per rename; der Ort steht in <Sicherung>/kaputt/ORT-DB.txt).
#   - Jeder Schritt wird protokolliert; ein gescheiterter Schritt bricht den Rückweg NICHT ab, er wird gesammelt.
#   - E15: fehlt die DB-Sicherung, obwohl der neue Code schon gegen die DB lief (Migrationen!), gibt es KEINEN
#     Code-Rückweg: lieber ein halber Dienst auf neuem Code als alter Code auf einer neuen DB.
#
# Ergebnis in HH_ROLLBACK_STATE (ok | unvollstaendig | unmoeglich), HH_ROLLBACK_FAILED, HH_ROLLBACK_MESSAGE.

HH_ROLLBACK_STATE=""
HH_ROLLBACK_FAILED=""
HH_ROLLBACK_MESSAGE=""

# Wurde der Dienst seit dem Start der Sicherung (neu) gestartet? Dann lief evtl. neuer Code gegen die DB (Migrationen),
# auch wenn update.sh den Neustart nicht selbst ausgelöst hat (andere Schritte, Timer, needrestart). Im Zweifel: ja.
hh_service_started_since() {
  local start=$1 since now_s ts
  case "$start" in [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]T[0-9][0-9][0-9][0-9][0-9][0-9]Z) ;; *) return 0 ;; esac
  since="$(date -u -d "${start:0:4}-${start:4:2}-${start:6:2} ${start:9:2}:${start:11:2}:${start:13:2}" +%s 2>/dev/null)" || return 0
  ts="$(systemctl show -p ActiveEnterTimestamp --value hydrahive2.service 2>/dev/null | head -1)"
  [ -n "$ts" ] || return 1
  now_s="$(date -d "$ts" +%s 2>/dev/null)" || return 0
  [ "$now_s" -ge "$since" ]
}

_rb_step() {   # <name> <befehl…>
  local name=$1; shift
  if "$@"; then
    log "Rückweg: $name – ok"
  else
    HH_ROLLBACK_FAILED="${HH_ROLLBACK_FAILED}${HH_ROLLBACK_FAILED:+, }$name"
    log "WARNUNG: Rückweg-Schritt '$name' fehlgeschlagen – weiter mit den nächsten"
  fi
  return 0
}

_rb_stop() {
  systemctl stop hydrahive2.service
  HH_RB_BRIDGE=0
  if systemctl cat hydra-voice-bridge.service >/dev/null 2>&1 && systemctl is-active --quiet hydra-voice-bridge.service; then
    systemctl stop hydra-voice-bridge.service && HH_RB_BRIDGE=1
  fi
  return 0
}

# Kaputten Stand zur Seite legen – BEVOR irgendetwas eingespielt wird.
_rb_kaputt() {
  local k="$HH_RB_DIR/kaputt" ddir f cfg_parent cfg_name
  ( umask 077; mkdir -p "$k" ) || return 1
  if [ "$HH_RB_NEED_DB" = 1 ]; then
    ddir="$(mktemp -d "$HH_DATA_DIR/.update-kaputt.XXXXXX")" || return 1
    chmod 700 "$ddir"
    printf '%s\n' "$ddir" > "$k/ORT-DB.txt"
    for f in sessions.db sessions.db-wal sessions.db-shm; do
      if [ -e "$HH_DATA_DIR/$f" ]; then mv "$HH_DATA_DIR/$f" "$ddir/" || return 1; fi
    done
  fi
  cfg_parent="$(dirname "$HH_CONFIG_DIR")"; cfg_name="$(basename "$HH_CONFIG_DIR")"
  ( umask 077; tar -C "$cfg_parent" -cf "$k/etc-hydrahive2-neu.tar" "$cfg_name" 2>/dev/null ) || true
  ( cd "$HH_REPO_DIR" && $HH_GIT diff --stat "$HH_RB_OLD" "${HH_RB_NEW:-HEAD}" > "$k/git-diff.stat" 2>&1 ) || true
  ( journalctl -u hydrahive2.service -n 300 --no-pager > "$k/journal.txt" 2>&1 ) || true
  chmod 600 "$k"/* 2>/dev/null || true
  return 0
}

_rb_code() {
  cd "$HH_REPO_DIR" || return 1
  $HH_GIT reset --hard "$HH_RB_OLD" >/dev/null || return 1
  [ "$($HH_GIT rev-parse HEAD)" = "$HH_RB_OLD" ]
}

# dist und frontend/src/modules aus der Sicherung (kein Neubau); der kaputte Stand bleibt als *.kaputt liegen.
_rb_frontend() {
  local fe="$HH_REPO_DIR/frontend" src
  rm -rf "$fe/dist.neu"
  if [ -d "$HH_RB_DIR/dist" ]; then src="$HH_RB_DIR/dist"; elif [ -d "$fe/dist.alt" ]; then src="$fe/dist.alt"; else
    log "Keine dist-Sicherung vorhanden – dist bleibt"; return 0
  fi
  rm -rf "$fe/dist.kaputt"
  if [ -e "$fe/dist" ]; then mv "$fe/dist" "$fe/dist.kaputt" || return 1; fi
  cp -a "$src" "$fe/dist" || return 1
  if [ -d "$HH_RB_DIR/modules-frontend" ]; then
    rm -rf "$fe/modules.kaputt"
    if [ -e "$fe/src/modules" ]; then mv "$fe/src/modules" "$fe/modules.kaputt" || return 1; fi
    cp -a "$HH_RB_DIR/modules-frontend" "$fe/src/modules" || return 1
  fi
  return 0
}

_rb_venv() {
  local v="$HH_REPO_DIR/.venv"
  if [ -f "$HH_RB_DIR/venv.tar.zst" ] || [ -f "$HH_RB_DIR/venv.tar.gz" ]; then
    rm -rf "$HH_REPO_DIR/.venv.kaputt"
    if [ -e "$v" ]; then mv "$v" "$HH_REPO_DIR/.venv.kaputt" || return 1; fi
    if [ -f "$HH_RB_DIR/venv.tar.zst" ]; then
      ( set -o pipefail; zstd -dc "$HH_RB_DIR/venv.tar.zst" | tar -C "$HH_REPO_DIR" -xf - ) || return 1
    else
      tar -C "$HH_REPO_DIR" -xzf "$HH_RB_DIR/venv.tar.gz" || return 1
    fi
    return 0
  fi
  [ -x "$v/bin/pip" ] || { log "Kein venv gesichert und kein pip – venv bleibt"; return 0; }
  sudo -u "$HH_USER" "$v/bin/pip" install -q -e "$HH_REPO_DIR/core"
}

_rb_db() {
  [ "$HH_RB_NEED_DB" = 1 ] || { log "Rückweg: Datenbank unverändert (kein Neustart mit neuem Code) – übersprungen"; return 0; }
  [ -n "$HH_RB_SNAP" ] || { log "Rückweg: keine DB gesichert (es gab keine) – frische DB beim Start"; return 0; }
  "$(hh_safety_python)" "$HH_DB_TOOL" restore "$HH_RB_SNAP" "$HH_DATA_DIR/sessions.db" "$HH_USER"
}

_rb_one_file() {   # <name-in-units> <ziel>  → 0 = geändert, 1 = gleich/fehlt
  local src="$HH_RB_DIR/units/$1" dst=$2
  [ -e "$src" ] || return 1
  cmp -s "$src" "$dst" 2>/dev/null && return 1
  cp -a "$src" "$dst"
}

_rb_config() {
  local cfg_parent cfg_name unit site sudo_f changed=0 nginx_changed=0
  cfg_parent="$(dirname "$HH_CONFIG_DIR")"; cfg_name="$(basename "$HH_CONFIG_DIR")"
  if [ -f "$HH_RB_DIR/etc-hydrahive2.tar" ]; then
    tar -C "$cfg_parent" -xpf "$HH_RB_DIR/etc-hydrahive2.tar" "$cfg_name" || return 1
  fi
  unit="${HH_UNIT_FILE:-/etc/systemd/system/hydrahive2.service}"
  site="${HH_NGINX_SITE:-/etc/nginx/sites-available/hydrahive2}"
  sudo_f="${HH_SUDOERS_FILE:-/etc/sudoers.d/hydrahive2-extensions}"
  _rb_one_file "$(basename "$unit")" "$unit" && changed=1
  if [ -d "$HH_RB_DIR/units/$(basename "$unit").d" ]; then
    mkdir -p "$unit.d" && cp -a "$HH_RB_DIR/units/$(basename "$unit").d/." "$unit.d/" && changed=1
  fi
  _rb_one_file "$(basename "$site")" "$site" && nginx_changed=1
  if [ -e "$HH_RB_DIR/units/$(basename "$sudo_f")" ]; then
    if ! command -v visudo >/dev/null 2>&1 || visudo -cf "$HH_RB_DIR/units/$(basename "$sudo_f")" >/dev/null 2>&1; then
      _rb_one_file "$(basename "$sudo_f")" "$sudo_f" || true
    else
      log "WARNUNG: gesicherte sudoers-Datei ist ungültig – nicht zurückgespielt"
      return 1
    fi
  fi
  [ "$changed" = 1 ] && systemctl daemon-reload
  if [ "$nginx_changed" = 1 ] && command -v nginx >/dev/null 2>&1; then
    nginx -t >/dev/null 2>&1 && systemctl reload nginx || return 1
  fi
  return 0
}

_rb_start_and_verify() {
  systemctl start hydrahive2.service || true
  if [ "${HH_RB_BRIDGE:-0}" = 1 ]; then systemctl start hydra-voice-bridge.service || log "WARNUNG: Voice-Bridge-Start fehlgeschlagen"; fi
  HH_NRESTARTS_BASE=""
  hh_safety_verify "$HH_RB_OLD" 1 || { log "Prüfung nach dem Rückweg: $HH_VERIFY_REASON"; return 1; }
}

# hh_rollback_run <sicherungsordner> <grund>
hh_rollback_run() {
  local dir=$1 reason=$2 short snap="" f
  set +e
  # Das DB-Werkzeug kommt aus der Sicherung, nicht aus dem Repo: nach dem Zurücksetzen des Codes ist es dort evtl. älter.
  if [ -f "$dir/db_snapshot.py" ] && grep -q "def restore" "$dir/db_snapshot.py" 2>/dev/null; then HH_DB_TOOL="$dir/db_snapshot.py"
  else HH_DB_TOOL="$HH_SAFETY_LIB_DIR/db_snapshot.py"; fi
  HH_RB_DIR="$dir"; HH_ROLLBACK_STATE=""; HH_ROLLBACK_FAILED=""; HH_ROLLBACK_MESSAGE=""
  HH_RB_OLD="$(hh_meta_get OLD_COMMIT "$dir")"; HH_RB_NEW="$(hh_meta_get NEW_COMMIT "$dir")"
  short="${HH_RB_OLD:0:8}"
  reason="${reason//$'\n'/ }"

  if [ -z "$HH_RB_OLD" ] || [ "$HH_RB_OLD" = "unbekannt" ]; then
    HH_ROLLBACK_STATE=unmoeglich
    HH_ROLLBACK_MESSAGE="$reason – Rückweg nicht möglich: alter Commit unbekannt, Sicherung in $dir"
    return 0
  fi
  for f in sessions.db.zst sessions.db.gz; do [ -f "$dir/$f" ] && snap="$dir/$f"; done
  HH_RB_SNAP="$snap"
  # War der neue Code schon gegen die DB gestartet (Migrationen!), ist die DB Teil des Rückwegs.
  HH_RB_NEED_DB=0
  if [ "$(hh_meta_get RESTARTED "$dir")" = "1" ] || hh_service_started_since "$(hh_meta_get START "$dir")"; then
    if [ "$(hh_meta_get DB_BACKED_UP "$dir")" = "1" ] || [ -f "$HH_DATA_DIR/sessions.db" ]; then HH_RB_NEED_DB=1; fi
  fi
  if [ "$HH_RB_NEED_DB" = 1 ] && [ "$(hh_meta_get DB_BACKED_UP "$dir")" = "1" ]; then
    # E15: ohne lesbare DB-Sicherung kein Code-Rückweg.
    if [ -z "$snap" ] || ! "$(hh_safety_python)" "$HH_DB_TOOL" verify "$snap" >/dev/null 2>&1; then
      HH_ROLLBACK_STATE=unmoeglich
      HH_ROLLBACK_MESSAGE="$reason – Rückweg nicht möglich: DB-Sicherung fehlt oder ist nicht lesbar, Sicherung in $dir"
      log "Rückweg NICHT durchgeführt: DB-Sicherung fehlt/ist unlesbar – der Dienst bleibt auf dem neuen Code (kein alter Code auf neuer DB)."
      return 0
    fi
  fi

  log "Update fehlgeschlagen ($reason) – Rückweg auf $short"
  _rb_step "Dienst anhalten" _rb_stop
  _rb_step "kaputten Stand zur Seite legen" _rb_kaputt
  _rb_step "Code auf $short" _rb_code
  _rb_step "Frontend (dist, Module)" _rb_frontend
  _rb_step "Python-venv" _rb_venv
  _rb_step "Datenbank" _rb_db
  _rb_step "Konfiguration und Units" _rb_config
  _rb_step "Dienst starten und prüfen" _rb_start_and_verify

  if [ -z "$HH_ROLLBACK_FAILED" ]; then
    HH_ROLLBACK_STATE=ok
    HH_ROLLBACK_MESSAGE="$reason – auf $short zurückgesetzt"
  else
    HH_ROLLBACK_STATE=unvollstaendig
    HH_ROLLBACK_MESSAGE="$reason – Rückweg unvollständig ($HH_ROLLBACK_FAILED), Sicherung in $dir"
  fi
  return 0
}
