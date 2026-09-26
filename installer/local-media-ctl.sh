#!/usr/bin/env bash
# HydraHive2 — Anfragen aus dem System-Fenster für Local Media ausführen.
#
# Aufgerufen von hydrahive2-local-media.service (root), sobald die API
# $HH_DATA_DIR/.local_media_request geschrieben hat. Die Datei enthält genau
# ein festes Wort: "install" oder "uninstall". Alles andere wird verworfen.
#
# Der Marker $HH_CONFIG_DIR/local-media.enabled steuert, ob update.sh Local
# Media weiter pflegt. Er wird erst nach erfolgreicher Installation gesetzt
# und nach dem Entfernen gelöscht.
set -uo pipefail

HH_REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
HH_DATA_DIR="${HH_DATA_DIR:-/var/lib/hydrahive2}"
HH_CONFIG_DIR="${HH_CONFIG_DIR:-/etc/hydrahive2}"
export HH_REPO_DIR HH_DATA_DIR HH_CONFIG_DIR

REQUEST="$HH_DATA_DIR/.local_media_request"
MARKER="$HH_CONFIG_DIR/local-media.enabled"
MODULES="$HH_REPO_DIR/installer/modules"

say() { printf '[hh2-media] %s\n' "$*"; }

[ -f "$REQUEST" ] || exit 0
action="$(head -c 16 "$REQUEST" | tr -d '[:space:]')"
# Die Anfrage bleibt bis zum Ende liegen: Die API meldet so "läuft" und lehnt
# weitere Klicks ab. Entfernt wird sie in jedem Fall, auch nach Fehlern.
trap 'rm -f "$REQUEST"' EXIT

say "===== $(date '+%F %T') Anfrage: ${action:-leer} ====="
case "$action" in
  install)
    if bash "$MODULES/72-local-media.sh"; then
      date +%s > "$MARKER"
      say "FERTIG: install ok"
      exit 0
    fi
    say "FEHLER: install fehlgeschlagen — siehe oben. Nichts eingeschaltet."
    exit 1
    ;;
  uninstall)
    if bash "$MODULES/72-local-media-uninstall.sh"; then
      rm -f "$MARKER"
      say "FERTIG: uninstall ok"
      exit 0
    fi
    say "FEHLER: uninstall fehlgeschlagen — siehe oben."
    exit 1
    ;;
  *)
    say "FEHLER: unbekannte Anfrage verworfen."
    exit 2
    ;;
esac
