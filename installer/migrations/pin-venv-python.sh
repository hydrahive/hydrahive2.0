#!/usr/bin/env bash
# Migration: venvs, deren Interpreter dem System-python3 folgt, festnageln.
#
# Hintergrund: `python3 -m venv X` verlinkt X/bin/python3 auf /usr/bin/python3.
# Die installierten Pakete liegen aber unter X/lib/python3.12/. Schwenkt das
# System-python3 auf eine neue Version (hier 3.12 -> 3.14), startet der venv
# mit dem falschen Interpreter und findet keines seiner Pakete mehr.
#
# So war SearXNG vom 29.08. bis 26.09.2026 ausgefallen: 364.199 Abstürze mit
# "ModuleNotFoundError: No module named 'msgspec'", systemd startete den
# Dienst jedes Mal neu, die Websuche aller Agents war vier Wochen tot.
#
# Die Migration prüft verwaltete venvs und setzt python/python3/python3.X
# auf den Interpreter, mit dem der venv gebaut wurde (aus pyvenv.cfg).
# Idempotent: korrekte venvs bleiben unverändert.
#
# Aufruf: sudo bash installer/migrations/pin-venv-python.sh
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

# Verwaltete venvs. Nur Pfade, die HydraHive selbst anlegt.
VENVS=(
  "/opt/searxng/venv"
)

fixed=0
for venv in "${VENVS[@]}"; do
  cfg="$venv/pyvenv.cfg"
  [ -f "$cfg" ] || continue

  # Nur reparieren, wenn der Link tatsächlich dem System-python3 folgt.
  [ "$(readlink "$venv/bin/python3" 2>/dev/null)" = "/usr/bin/python3" ] || continue

  # Bauversion aus pyvenv.cfg: "version = 3.12.3" -> "3.12"
  built="$(sed -n 's/^version *= *\([0-9]*\.[0-9]*\).*/\1/p' "$cfg" | head -1)"
  target="/usr/bin/python${built}"
  if [ -z "$built" ] || [ ! -x "$target" ]; then
    log "WARNUNG: $venv wurde mit Python $built gebaut, $target fehlt — nicht repariert"
    continue
  fi

  running="$("$venv/bin/python3" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo "?")"
  if [ "$running" = "$built" ]; then
    continue  # folgt zwar dem System-Link, passt aber (noch)
  fi

  owner="$(stat -c '%U:%G' "$venv/bin")"
  log "$venv: läuft mit Python $running, gebaut mit $built — fixiere auf $target"
  ln -sfn "$target" "$venv/bin/python${built}"
  ln -sfn "python${built}" "$venv/bin/python3"
  ln -sfn "python${built}" "$venv/bin/python"
  chown -h "$owner" "$venv/bin/python" "$venv/bin/python3" "$venv/bin/python${built}"
  fixed=1
done

if [ "$fixed" = "1" ] && systemctl list-unit-files searxng.service >/dev/null 2>&1; then
  log "SearXNG neu starten"
  systemctl reset-failed searxng.service 2>/dev/null || true
  systemctl restart searxng.service || log "WARNUNG: SearXNG-Neustart fehlgeschlagen"
fi
