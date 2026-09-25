#!/usr/bin/env bash
# Voice-Migration: STT-Inferenz-Tuning für bestehende Container.
#
# Hintergrund: wyoming-faster-whisper lief ohne --compute-type, also in
# float32. Auf CPU ist das reine Verschwendung — int8 liefert bei gleichem
# Modell dieselbe Transkript-Qualität in der halben Zeit. Gemessen auf
# Ryzen 5 4500 mit 21,6s Diktat und Modell 'medium':
#
#   float32, beam 5 : 20,5s  (RTF 0,95 — Warten ≈ Sprechdauer)
#   int8,    beam 5 : 13,1s  (RTF 0,61)
#   int8,    beam 1 :  9,7s  (RTF 0,45)
#
# Zusätzlich: --initial-prompt stand auf Smart-Home-Kommandos. Beim Diktat
# von Code-Anweisungen im Chat schadet das ("refakturiere" statt
# "refaktoriere", "komm mit" statt "commit"). Der Prompt deckt jetzt beide
# Fälle ab. Kostet keine Laufzeit.
#
# Idempotent: läuft mehrfach ohne Schaden. Ein bereits getunter Container
# wird erkannt und übersprungen.
#
# WICHTIG: Das konfigurierte Modell wird bewusst ERHALTEN. Wer auf 'medium'
# gewechselt hat (bessere Erkennung von Fachbegriffen wie ffmpeg/pytest),
# behält 'medium'. Diese Migration ändert nur, WIE gerechnet wird.
#
# Aufruf: sudo bash installer/migrations/voice-stt-perf.sh
set -euo pipefail

CT_NAME="${CT_NAME:-hydrahive2-stt}"
UNIT_PATH="/etc/systemd/system/wyoming-whisper.service"

log() { printf "  · %s\n" "$*"; }

if ! command -v incus >/dev/null 2>&1; then
  log "incus nicht installiert — kein Voice-Stack, nichts zu tun."
  exit 0
fi

if ! incus list --format=csv -c n 2>/dev/null | grep -qx "$CT_NAME"; then
  log "Container '$CT_NAME' existiert nicht — nichts zu tun."
  exit 0
fi

if ! incus list --format=csv -c n,s 2>/dev/null | grep -qx "$CT_NAME,RUNNING"; then
  log "Container '$CT_NAME' läuft nicht — starte für Migration"
  incus start "$CT_NAME" >/dev/null 2>&1 || true
  sleep 3
fi

current="$(incus exec "$CT_NAME" -- cat "$UNIT_PATH" 2>/dev/null || true)"
if [ -z "$current" ]; then
  log "Keine Unit '$UNIT_PATH' im Container — 55-voice.sh legt sie an, überspringe."
  exit 0
fi

if printf '%s' "$current" | grep -q -- "--compute-type"; then
  log "STT-Tuning bereits aktiv — nichts zu tun."
  exit 0
fi

# Konfiguriertes Modell aus der laufenden Unit übernehmen (Default: small).
model="$(printf '%s' "$current" \
  | sed -n 's/.*--model[= ]\([A-Za-z0-9._-]*\).*/\1/p' | head -1)"
[ -n "$model" ] || model="small"
log "Vorhandenes Modell '$model' wird beibehalten"

# Sprach-Flag ebenfalls erhalten — sonst verliert ein auf 'de' gepinnter
# Container seine Sprache und fällt auf Auto-Detect zurück.
lang="$(printf '%s' "$current" \
  | sed -n 's/.*--language[= ]\([A-Za-z-]*\).*/\1/p' | head -1)"
lang_flag=""
if [ -n "$lang" ]; then
  lang_flag=" --language $lang"
  log "Sprache '$lang' wird beibehalten"
fi

log "Backup der Unit → ${UNIT_PATH}.pre-perf"
incus exec "$CT_NAME" -- cp "$UNIT_PATH" "${UNIT_PATH}.pre-perf"

log "Unit mit int8 + beam-size 1 + Diktat-Prompt neu schreiben"
incus exec "$CT_NAME" -- env \
  HH_MODEL="$model" HH_LANG_FLAG="$lang_flag" HH_UNIT="$UNIT_PATH" \
  bash -c 'cat > "$HH_UNIT" <<EOF
[Unit]
Description=Wyoming faster-whisper STT
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/opt/wyoming/bin/wyoming-faster-whisper --model ${HH_MODEL} --uri tcp://0.0.0.0:10300 --data-dir /var/lib/wyoming${HH_LANG_FLAG} --compute-type int8 --beam-size 1 --vad-filter --initial-prompt "Diktat fuer Smart-Home-Befehle und Software-Entwicklung auf Deutsch: Python, git, commit, branch, refactor, pytest, ffmpeg, API-Endpoint. Mit korrekter Zeichensetzung."
Restart=on-failure
RestartSec=5
WorkingDirectory=/var/lib/wyoming
StateDirectory=wyoming

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload'

# Container-Neustart statt `systemctl restart`. In unprivilegierten LXCs
# kann systemd die cgroup des alten Prozesses nicht killen ("Failed to kill
# control group: Permission denied") — der alte Whisper hält Port 10300
# weiter, der neue crasht in einer Restart-Schleife an "address already in
# use", und die alte Unit läuft unbemerkt weiter. Ein Container-Restart
# räumt zuverlässig auf.
log "Container neu starten (räumt alten Whisper-Prozess sicher ab)"
incus restart "$CT_NAME" >/dev/null 2>&1

# Verifikation: Es muss GENAU EIN Prozess laufen — und zwar mit den neuen
# Flags. Ein reiner Port-Check würde den überlebenden alten Prozess sehen
# und fälschlich Erfolg melden.
ok=0
for _ in $(seq 1 45); do
  running="$(incus exec "$CT_NAME" -- \
    pgrep -af wyoming-faster-whisper 2>/dev/null || true)"
  if printf '%s' "$running" | grep -q -- "--compute-type int8" \
     && incus exec "$CT_NAME" -- ss -tln 2>/dev/null | grep -q ":10300"; then
    ok=1
    break
  fi
  sleep 2
done

if [ "$ok" = "1" ]; then
  log "STT-Tuning aktiv — Modell '$model', int8, beam-size 1."
else
  log "FEHLER: STT startet mit neuen Flags nicht — Rollback auf alte Unit"
  incus exec "$CT_NAME" -- bash -c "
    cp '${UNIT_PATH}.pre-perf' '$UNIT_PATH'
    systemctl daemon-reload" || true
  incus restart "$CT_NAME" >/dev/null 2>&1 || true
  exit 1
fi
