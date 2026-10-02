#!/usr/bin/env bash
# Migration: SearXNG-Bestand angleichen (Spec docs/specs/websearch-blocked-engines.md §7).
#
# 1. Alte Installer-Versionen schrieben die Einstellungen in SearXNGs
#    mitgelieferte Standarddatei (searx/settings.yml). Wird dort reingezeigt:
#    Standarddatei wiederherstellen, eigene Datei unter searxng/settings.yml.
# 2. Bing und Yandex einschalten, falls nicht vorhanden. Am 02.10.2026 waren
#    DuckDuckGo/Startpage (CAPTCHA), Brave (zu viele Anfragen) und Google
#    (leer) gesperrt; die Websuche lieferte unbemerkt 0 Treffer.
#
# Idempotent. Sicherung vor jeder Änderung; bei 0 Treffern nach dem Neustart
# wird die Sicherung zurückgespielt. Bricht das Update nie ab.
#
# Aufruf: sudo bash installer/migrations/searxng-engines.sh
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

UNIT="/etc/systemd/system/searxng.service"
SEARXNG_DIR="/opt/searxng"
OWN_SETTINGS="$SEARXNG_DIR/searxng/settings.yml"
OLD_SETTINGS="$SEARXNG_DIR/searx/settings.yml"
VENV_PY="$SEARXNG_DIR/venv/bin/python"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MERGE_PY="$HERE/../lib/searxng_engines.py"
PORT="${HH_SEARXNG_PORT:-8888}"
STAMP="$(date +%Y%m%d-%H%M%S)"

[ -f "$UNIT" ] || exit 0          # SearXNG nicht installiert
[ -x "$VENV_PY" ] || { log "SearXNG-venv fehlt — übersprungen"; exit 0; }

settings="$(sed -n 's/^Environment=SEARXNG_SETTINGS_PATH=//p' "$UNIT" | head -1)"
[ -n "$settings" ] || { log "SEARXNG_SETTINGS_PATH nicht in der Unit — übersprungen"; exit 0; }

unit_changed=0
if [ "$settings" = "$OLD_SETTINGS" ]; then
  log "Einstellungen zeigen auf SearXNGs Standarddatei — auf eigene Datei umstellen"
  install -d -m 0755 -o searxng -g searxng "$(dirname "$OWN_SETTINGS")"
  mkdir -p /var/backups
  cp -a "$OLD_SETTINGS" "/var/backups/searxng-default-settings-$STAMP.yml"
  if [ ! -f "$OWN_SETTINGS" ]; then
    cp -a "$OLD_SETTINGS" "$OWN_SETTINGS"
  fi
  if [ -d "$SEARXNG_DIR/.git" ]; then
    git -c safe.directory="$SEARXNG_DIR" -C "$SEARXNG_DIR" checkout -- searx/settings.yml \
      || log "WARNUNG: Standarddatei nicht wiederherstellbar"
  fi
  sed -i "s#^Environment=SEARXNG_SETTINGS_PATH=.*#Environment=SEARXNG_SETTINGS_PATH=$OWN_SETTINGS#" "$UNIT"
  systemctl daemon-reload
  settings="$OWN_SETTINGS"
  unit_changed=1
fi

[ -f "$settings" ] || { log "Einstellungsdatei $settings fehlt — übersprungen"; exit 0; }

mkdir -p /var/backups
backup="/var/backups/searxng-settings-$STAMP.yml"
cp -a "$settings" "$backup"
result="$("$VENV_PY" "$MERGE_PY" "$settings" 2>&1)" || {
  log "WARNUNG: Suchanbieter nicht ergänzt: $result"
  result="unchanged"
}

if [ "$result" != "changed" ] && [ "$unit_changed" = "0" ]; then
  rm -f "$backup"             # nichts geändert, keine Sicherung nötig
  exit 0
fi
[ "$result" = "changed" ] && log "Bing und Yandex in $settings eingeschaltet (Sicherung: $backup)"

log "SearXNG neu starten und prüfen"
systemctl reset-failed searxng.service 2>/dev/null || true
systemctl restart searxng.service || log "WARNUNG: Neustart fehlgeschlagen"

hits=0
for _ in $(seq 1 20); do
  hits="$(curl -s -m 20 "http://127.0.0.1:$PORT/search?q=wikipedia&format=json" \
    | "$VENV_PY" -c 'import json,sys; print(len(json.load(sys.stdin).get("results") or []))' 2>/dev/null || echo 0)"
  [ "$hits" -gt 0 ] 2>/dev/null && break
  sleep 2
done

if [ "$hits" -gt 0 ] 2>/dev/null; then
  log "Websuche liefert $hits Treffer"
elif [ "$result" = "changed" ]; then
  log "WARNUNG: 0 Treffer nach der Änderung — Sicherung zurückspielen"
  cp -a "$backup" "$settings"
  systemctl restart searxng.service || true
else
  log "WARNUNG: Websuche liefert 0 Treffer — Dienst prüfen (journalctl -u searxng)"
fi
