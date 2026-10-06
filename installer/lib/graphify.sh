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

  if [ -x "$venv/bin/graphify" ]; then
    $log_fn "graphify vorhanden ($("$venv/bin/graphify" --version 2>/dev/null | head -1))"
    return 0
  fi
  $log_fn "graphify für den Code-Graph installieren ($venv)"
  install -d -o "$user" -g "$user" -m 0775 "$data_dir/tools" "$data_dir/tools/graphify"
  # Als Dienst-User, damit HydraHive das venv später selbst aktualisieren kann.
  if ! runuser -u "$user" -- "$py" -m venv "$venv" \
     || ! runuser -u "$user" -- "$venv/bin/pip" install --quiet --disable-pip-version-check graphifyy; then
    $log_fn "WARNUNG: graphify-Installation fehlgeschlagen — HydraHive versucht es beim ersten Bauen erneut"
    return 0
  fi
  $log_fn "graphify installiert ($("$venv/bin/graphify" --version 2>/dev/null | head -1))"
}
