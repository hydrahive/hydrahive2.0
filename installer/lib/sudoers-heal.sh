#!/usr/bin/env bash
# Bestandsmigration der sudoers-Datei für HydraHive (Task ddec8288). Wird von update.sh gesourct, idempotent.
#
# Ältere Installationen schrieben `Defaults:<user> !requiretty` in /etc/sudoers.d/hydrahive2-extensions. sudo-rs
# (Standard ab Ubuntu 26.04) kennt `requiretty` nicht: `visudo -c` lehnt die Datei ab, jeder sudo-Aufruf meldet
# „unknown setting“, und frühere sudo-rs-Versionen verwarfen die ganze Datei (Prod-Upgrade 20.08.2026). 50-systemd.sh
# schreibt die Zeile seit 39ecfca6 nicht mehr – bestehende Dateien hat update.sh aber nie angefasst.
#
# Ablauf: Zeile in einer Kopie entfernen, Kopie mit `visudo -c -f` prüfen, nur bei Erfolg atomar ersetzen
# (Rechte 0440, Besitzer bleibt). Lehnt visudo ab, bleibt die alte Datei und es gibt eine Warnung.

hh_sudoers_log() {
  if declare -F log >/dev/null 2>&1; then log "$*"; else printf '  · %s\n' "$*"; fi
}

# hh_fix_sudoers_requiretty <datei> <user>
hh_fix_sudoers_requiretty() {
  local file="$1" user="$2" tmp pattern
  [ -f "$file" ] || return 0
  # Genau `Defaults:<user> !requiretty` (Leerzeichen und Kommentar dahinter erlaubt). Kommentarzeilen und andere
  # Defaults bleiben. Der Nutzername kommt aus HH_USER und wird für das Muster entschärft.
  pattern="^[[:space:]]*Defaults:$(printf '%s' "$user" | sed 's/[][\.*^$/]/\\&/g')[[:space:]]+!requiretty[[:space:]]*(#.*)?$"
  grep -Eq "$pattern" "$file" 2>/dev/null || return 0

  tmp="$(mktemp "$(dirname "$file")/.$(basename "$file").XXXXXX")" || return 0
  grep -Ev "$pattern" "$file" > "$tmp" || true
  chmod 0440 "$tmp"
  chown --reference="$file" "$tmp" 2>/dev/null || true
  if visudo -c -f "$tmp" >/dev/null 2>&1; then
    mv -f "$tmp" "$file"
    hh_sudoers_log "sudoers: veraltete Zeile 'Defaults:$user !requiretty' aus $file entfernt (sudo-rs kennt sie nicht)"
  else
    rm -f "$tmp"
    hh_sudoers_log "WARNUNG: $file enthält 'Defaults:$user !requiretty', die bereinigte Fassung besteht visudo nicht – unverändert gelassen. Bitte prüfen: sudo visudo -c -f $file"
  fi
  return 0
}
