#!/usr/bin/env bash
# Voice-Migration: alter Docker-STT-Stack → neuer incus-LXC-Stack.
#
# Wird automatisch von 55-voice.sh am Ende ausgeführt wenn der neue
# incus-Container healthy ist. Kann aber manuell genutzt werden um
# alte Docker-Reste explizit aufzuräumen ohne 55-voice.sh komplett
# durchzulaufen.
#
# Aufruf: sudo bash installer/migrations/voice-docker-to-incus.sh
set -euo pipefail

log() { printf "  · %s\n" "$*"; }

if ! command -v docker >/dev/null 2>&1; then
  log "Docker nicht installiert — nichts zu migrieren."
  exit 0
fi

removed_any=0
for name in hydrahive2-stt hydrahive2-tts; do
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$name"; then
    log "Entferne Docker-Container '$name'"
    docker rm -f "$name" >/dev/null 2>&1 || true
    removed_any=1
  fi
done

if [ "$removed_any" = "0" ]; then
  log "Keine Docker-Voice-Container gefunden — schon migriert oder nie da."
fi

# Compose-File aus alter Welt
if [ -d /opt/hydrahive2-voice ]; then
  log "Altes Compose-Verzeichnis /opt/hydrahive2-voice → /opt/hydrahive2-voice.bak"
  rm -rf /opt/hydrahive2-voice.bak
  mv /opt/hydrahive2-voice /opt/hydrahive2-voice.bak
fi

log ""
log "Migration durch."
log "Docker-Daemon bleibt installiert — kein automatisches Deinstall."
log "Wenn du Docker komplett los werden willst:"
log "  sudo apt-get remove -y docker-ce docker-ce-cli containerd.io docker-compose-plugin"
log "  sudo rm -rf /var/lib/docker"
