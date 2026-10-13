#!/usr/bin/env bash
# SearXNG-venv auf den Interpreter von hh_pick_python bringen (Spec
# docs/specs/python-314-umstieg.md). Wird gesourct, braucht python-venv.sh.
#
# Passt das venv nicht (andere Version, bin/python zeigt ins Leere, kein pip),
# wird es mit --clear neu gebaut und requirements.txt neu installiert — so läuft
# SearXNG auf Prod seit Juni (`python -m searx.webapp` aus dem Checkout).
# Passt es, bleibt es unangetastet. Setzt HH_VENV_REBUILT auf 0 oder 1.
#
# Aufruf: hh_searxng_sync_venv <searxng-dir> <user> <dienst|"">

hh_searxng_sync_venv() {
  local dir="$1" owner="$2" service="${3:-}"
  local venv="$dir/venv"
  local marker="$venv/.hh-incomplete"

  # Abgebrochener Neubau vom letzten Mal: venv ist leer, wirkt aber gesund.
  if [ -e "$marker" ]; then
    hh_venv_log "SearXNG-venv unvollständig (letzter Neubau abgebrochen) — neu aufbauen"
    rm -f -- "$venv/bin/python"
  fi

  hh_ensure_python_venv "$venv" "$owner" "$service" "$dir" || return 1
  [ "$HH_VENV_REBUILT" = "1" ] || return 0

  hh_run_as_owner "$owner" touch "$marker"
  hh_venv_log "SearXNG-Pakete in neues venv installieren"
  # Jeder Schritt einzeln geprüft: der Aufrufer nutzt die Funktion in einer
  # ||-Kette, dort greift `set -e` nicht.
  hh_run_as_owner "$owner" "$venv/bin/python" -m pip install -q --upgrade pip setuptools wheel || return 1
  # requirements.txt enthält msgspec und die übrigen Laufzeit-Abhängigkeiten.
  if [ -f "$dir/requirements.txt" ]; then
    hh_run_as_owner "$owner" "$venv/bin/python" -m pip install -q -r "$dir/requirements.txt" || return 1
  fi
  rm -f -- "$marker"
}
