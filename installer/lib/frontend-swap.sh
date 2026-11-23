#!/usr/bin/env bash
# Frontend-Bau in dist.neu + Tausch gegen dist (docs/specs/update-rollback.md, Etappe U2).
#
# nginx liefert frontend/dist aus (installer/modules*/60-nginx.sh). Gebaut wird deshalb nie direkt dorthin:
# vite schreibt nach frontend/dist.neu (Umgebungsvariable HH_FRONTEND_OUTDIR, frontend/vite.config.ts), und erst
# ein vollständiger Bau ersetzt dist. Scheitert der Bau (TS-Fehler, rollup-Fehler, Abbruch), bleibt dist unberührt.
#
# Der Tausch sind zwei rename() im selben Verzeichnis (dist → dist.alt, dist.neu → dist), kein Kopieren.
# Dazwischen liegt nur ein Augenblick ohne dist. Schlägt der zweite rename fehl, kommt dist.alt zurück.
# dist.alt bleibt bis zum nächsten Bau liegen (Grundlage für den Rückweg, U3/U4).
#
# Rein Bash 3.2-tauglich (macOS), keine Abhängigkeit zu log/err des Aufrufers.

# hh_frontend_prepare <frontend-dir>: Reste eines früheren (abgebrochenen) Baus entfernen.
hh_frontend_prepare() {
  local fe=$1
  rm -rf "$fe/dist.neu"
}

# hh_frontend_swap <frontend-dir>: dist.neu wird dist. Rückgabe 0 = getauscht; 1 = nicht getauscht, dist unverändert.
hh_frontend_swap() {
  local fe=$1
  if [ ! -f "$fe/dist.neu/index.html" ]; then
    echo "dist.neu enthält keinen fertigen Build (index.html fehlt) – dist bleibt unverändert" >&2
    return 1
  fi
  rm -rf "$fe/dist.alt"
  if [ -e "$fe/dist" ]; then
    mv "$fe/dist" "$fe/dist.alt" || { echo "dist konnte nicht beiseite gelegt werden" >&2; return 1; }
  fi
  if ! mv "$fe/dist.neu" "$fe/dist"; then
    [ -e "$fe/dist.alt" ] && mv "$fe/dist.alt" "$fe/dist"
    echo "Tausch dist.neu → dist fehlgeschlagen – alter Stand zurückgelegt" >&2
    return 1
  fi
  return 0
}

# hh_frontend_discard <frontend-dir>: nach einem fehlgeschlagenen Bau den Halbbau wegräumen.
hh_frontend_discard() {
  local fe=$1
  rm -rf "$fe/dist.neu"
}
