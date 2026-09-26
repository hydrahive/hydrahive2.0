#!/usr/bin/env bash
# HydraHive2 — lokale Bild-/Videogenerierung (ComfyUI) wieder entfernen.
#
# Gegenstück zu 72-local-media.sh. Entfernt Container, Image, Modelle,
# ComfyUI-Daten und den Backend-Eintrag "local-gpu" in llm.json. Docker und
# das NVIDIA Container Toolkit bleiben, andere Extensions können sie nutzen.
# Den Marker local-media.enabled entfernt der Aufrufer (local-media-ctl.sh).
set -euo pipefail

log() { printf '\033[1;36m[hh2-media]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[hh2-media]\033[0m %s\n' "$*" >&2; }
err() { printf '\033[1;31m[hh2-media]\033[0m %s\n' "$*" >&2; exit 1; }

[ "${HH_LOCAL_MEDIA_SKIP_ROOT_CHECK:-}" = 1 ] || [ "$(id -u)" -eq 0 ] || err "Dieses Modul muss als root laufen."

CONFIG_DIR="${HH_CONFIG_DIR:-/etc/hydrahive2}"
MEDIA_ROOT="${HH_MEDIA_ROOT-/var/lib/hydrahive2/local-media}"
MEDIA_IMAGE="${HH_MEDIA_IMAGE:-yanwk/comfyui-boot:cu128-slim}"
CONTAINER=hydra-comfyui

# Schutz vor dem Löschen falscher Verzeichnisse: nur absolute Pfade, nicht /,
# und nur wenn dort erkennbar eine Local-Media-Struktur liegt (oder nichts).
case "$MEDIA_ROOT" in
  /*) ;;
  *) err "HH_MEDIA_ROOT muss ein absoluter Pfad sein: '${MEDIA_ROOT}'" ;;
esac
MEDIA_ROOT="$(realpath -m "$MEDIA_ROOT")"
[ "$MEDIA_ROOT" != "/" ] || err "HH_MEDIA_ROOT darf nicht / sein."
if [ -d "$MEDIA_ROOT" ] && [ -n "$(ls -A "$MEDIA_ROOT")" ] \
   && [ ! -d "$MEDIA_ROOT/models" ] && [ ! -d "$MEDIA_ROOT/data" ]; then
  err "$MEDIA_ROOT sieht nicht nach Local Media aus (kein models/ oder data/) — nichts gelöscht."
fi

if command -v docker >/dev/null 2>&1; then
  log "Container $CONTAINER entfernen"
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  log "Image $MEDIA_IMAGE entfernen"
  docker image rm "$MEDIA_IMAGE" >/dev/null 2>&1 || warn "Image nicht entfernt (noch in Benutzung oder schon weg)."
fi

LLM_CONFIG="$CONFIG_DIR/llm.json"
if [ -f "$LLM_CONFIG" ]; then
  log "Backend local-gpu aus llm.json austragen"
  export LLM_CONFIG
  python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["LLM_CONFIG"])
data = json.loads(path.read_text())
data["media_backends"] = [b for b in data.get("media_backends", []) if b.get("id") != "local-gpu"]
# Standard-Modelle, die auf das entfernte Backend zeigen, würden ins Leere
# generieren. Sie werden geleert, dann greift wieder der Cloud-Standard.
models = data.get("media_models") or {}
for key in [k for k, v in models.items() if isinstance(v, str) and v.startswith("local:local-gpu/")]:
    del models[key]
tmp = path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
os.chmod(tmp, path.stat().st_mode & 0o777)
try:
    os.chown(tmp, path.stat().st_uid, path.stat().st_gid)
except PermissionError:
    pass
tmp.replace(path)
PY
fi

rm -f "$CONFIG_DIR/local-media.env"

if [ -d "$MEDIA_ROOT" ]; then
  log "Modelle und ComfyUI-Daten löschen: $MEDIA_ROOT ($(du -sh "$MEDIA_ROOT" 2>/dev/null | cut -f1))"
  rm -rf --one-file-system -- "$MEDIA_ROOT"
fi

log "Local Media Runtime entfernt."
