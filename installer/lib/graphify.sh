#!/usr/bin/env bash
# graphify für den Code-Graph vorinstallieren (core/src/hydrahive/code_graph_install.py).
#
# HydraHive legt das venv sonst erst beim ersten "Graph bauen" an: pip lädt dann
# minutenlang, und der Nutzer sieht nur einen hängenden Button. Pfad und Paket
# MÜSSEN mit code_graph_install.py übereinstimmen.
#
# Wird gesourct; idempotent. Fehler sind nicht fatal: HydraHive versucht es beim
# ersten Bauen erneut.

ensure_graphify() {
  local data_dir="${HH_DATA_DIR:-/var/lib/hydrahive2}"
  local user="${HH_USER:-hydrahive}"
  local venv="$data_dir/tools/graphify/venv"
  # Gleiches Python wie HydraHive (code_graph_install nutzt sys.executable).
  local py="${HH_REPO_DIR:-/opt/hydrahive2}/.venv/bin/python"
  [ -x "$py" ] || py=python3
  local log_fn=log
  declare -F log >/dev/null 2>&1 || log_fn=echo

  # „Vorhanden“ heißt: graphify da UND gleiche Python-Version wie HydraHive.
  # Nach einem Python-Wechsel (Ubuntu 26.04: 3.12 → 3.14) zeigt bin/python
  # sonst auf den alten oder einen entfernten Interpreter (Spec python-314-umstieg).
  local want have
  want="$("$py" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
  have="$("$venv/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
  if [ -x "$venv/bin/graphify" ] && [ -n "$want" ] && [ "$want" = "$have" ]; then
    $log_fn "graphify vorhanden ($("$venv/bin/graphify" --version 2>/dev/null | head -1))"
    return 0
  fi
  $log_fn "graphify für den Code-Graph installieren ($venv, Python ${want:-?}, bisher ${have:-keins})"
  install -d -o "$user" -g "$user" -m 0775 "$data_dir/tools" "$data_dir/tools/graphify"
  # Als Dienst-User, damit HydraHive das venv später selbst aktualisieren kann.
  # --clear: ein veraltetes venv wird vollständig ersetzt.
  if ! runuser -u "$user" -- "$py" -m venv --clear "$venv" \
     || ! runuser -u "$user" -- "$venv/bin/pip" install --quiet --disable-pip-version-check graphifyy; then
    $log_fn "WARNUNG: graphify-Installation fehlgeschlagen — HydraHive versucht es beim ersten Bauen erneut"
    return 0
  fi
  $log_fn "graphify installiert ($("$venv/bin/graphify" --version 2>/dev/null | head -1))"
}
