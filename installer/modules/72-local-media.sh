#!/usr/bin/env bash
# HydraHive2 — optionale lokale Media-Runtime (GPU-Node).
# Idempotent: auf Maschinen ohne NVIDIA-GPU wird sauber übersprungen.
set -euo pipefail

log() { printf '\033[1;36m[hh2-media]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[hh2-media]\033[0m %s\n' "$*" >&2; }
err() { printf '\033[1;31m[hh2-media]\033[0m %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Dieses Modul muss als root laufen."
command -v nvidia-smi >/dev/null 2>&1 || { log "Keine NVIDIA-GPU erkannt — Local Media übersprungen."; exit 0; }
command -v apt-get >/dev/null 2>&1 || err "apt-get wird für die GPU-Runtime benötigt."

export DEBIAN_FRONTEND=noninteractive
if ! command -v docker >/dev/null 2>&1; then
  log "Docker installieren"
  apt-get update -qq
  apt-get install -y -qq docker.io
  systemctl enable --now docker
fi

# NVIDIA Container Toolkit aus dem offiziellen, signierten NVIDIA-Repository.
# Die Konfiguration ist idempotent und wird nur bei fehlendem GPU-Runtime-Test
# ausgeführt. Keine User-Eingaben werden in Shell-Code interpoliert.
if ! command -v nvidia-ctk >/dev/null 2>&1; then
  log "NVIDIA Container Toolkit installieren"
  apt-get update -qq
  apt-get install -y -qq curl ca-certificates gpg
  install -d -m 0755 /usr/share/keyrings
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#^deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#' \
    > /etc/apt/sources.list.d/nvidia-container-toolkit.list
  apt-get update -qq
  apt-get install -y -qq nvidia-container-toolkit
  nvidia-ctk runtime configure --runtime=docker
  systemctl restart docker
fi

# Ein kleiner CUDA-Test verhindert, dass ein kaputtes Toolkit erst beim
# ComfyUI-Start auffällt.
if ! docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 \
    nvidia-smi >/dev/null 2>&1; then
  err "NVIDIA-Docker-Runtime ist nicht funktionsfähig. Treiber/Kernel prüfen."
fi

MEDIA_ROOT="${HH_MEDIA_ROOT:-/var/lib/hydrahive2/local-media}"
MEDIA_IMAGE="${HH_MEDIA_IMAGE:-yanwk/comfyui-boot:cu128-slim}"
REPO_DIR="${HH_REPO_DIR:-/opt/hydrahive2}"
install -d -m 0755 "$MEDIA_ROOT/data" "$MEDIA_ROOT/models"/{checkpoints,diffusion_models,text_encoders,vae}

# Öffentliche, versionsgebundene Basismodelle. Unvollständige Downloads werden
# fortgesetzt; erst die Mindestgröße markiert eine Datei als verwendbar.
download_model() {
  local url="$1" target="$2" min_bytes="$3" expected_sha="$4" size=0 actual_sha=""
  [ -f "$target" ] && size="$(stat -c %s "$target" 2>/dev/null || echo 0)"
  if [ "$size" -ge "$min_bytes" ]; then
    actual_sha="$(sha256sum "$target" | cut -d' ' -f1)"
    if [ "$actual_sha" = "$expected_sha" ]; then
      log "Modell vorhanden: $(basename "$target")"
      return 0
    fi
    warn "Prüfsumme falsch, lade Modell neu: $(basename "$target")"
    rm -f "$target"
  fi
  log "Modell laden/fortsetzen: $(basename "$target")"
  curl -fL --retry 5 --retry-delay 5 --continue-at - "$url" -o "$target"
  size="$(stat -c %s "$target")"
  [ "$size" -ge "$min_bytes" ] || err "Modelldownload unvollständig: $target"
  actual_sha="$(sha256sum "$target" | cut -d' ' -f1)"
  [ "$actual_sha" = "$expected_sha" ] || err "Modelldownload hat eine ungültige Prüfsumme: $target"
}

download_model \
  "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors" \
  "$MEDIA_ROOT/models/checkpoints/sd_xl_base_1.0.safetensors" 6900000000 \
  "31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b"
download_model \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors" \
  "$MEDIA_ROOT/models/diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors" 2800000000 \
  "be531024cd9018cb5b48c40cfbb6a6191645b1c792eb8bf4f8c1c6e10f924dc5"
download_model \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
  "$MEDIA_ROOT/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" 6700000000 \
  "c3355d30191f1f066b26d93fba017ae9809dce6c627dda5f6a66eaa651204f68"
download_model \
  "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors" \
  "$MEDIA_ROOT/models/vae/wan_2.1_vae.safetensors" 250000000 \
  "2fc39d31359a4b0a64f55876d8ff7fa8d780956ae2cb13463b0223e15148976b"

log "ComfyUI-Image aktualisieren: $MEDIA_IMAGE"
docker pull "$MEDIA_IMAGE" >/dev/null

docker rm -f hydra-comfyui >/dev/null 2>&1 || true
log "ComfyUI localhost-only starten"
# SDXL benötigt auf 16-GiB-Karten Low-VRAM-Offloading; größere Karten bleiben
# im schnelleren Normalmodus. Der Grenzwert wird aus nvidia-smi abgeleitet.
VRAM_MIB="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')"
COMFY_ARGS=""
[ "${VRAM_MIB:-0}" -lt 20000 ] && COMFY_ARGS="--lowvram"
docker run -d --name hydra-comfyui --restart unless-stopped --gpus all \
  -e "CLI_ARGS=$COMFY_ARGS" \
  -p 127.0.0.1:8188:8188 \
  -v "$MEDIA_ROOT/data:/root/ComfyUI" \
  -v "$MEDIA_ROOT/models:/root/ComfyUI/models" \
  "$MEDIA_IMAGE" >/dev/null

install -d -m 0755 "${HH_CONFIG_DIR:-/etc/hydrahive2}"
cat > "${HH_CONFIG_DIR:-/etc/hydrahive2}/local-media.env" <<EOF
# Automatisch verwaltet — Local Media Runtime
HH_MEDIA_API_BASE=http://127.0.0.1:8188
HH_MEDIA_CONTAINER=hydra-comfyui
HH_MEDIA_IMAGE=$MEDIA_IMAGE
HH_MEDIA_ROOT=$MEDIA_ROOT
EOF
chmod 0644 "${HH_CONFIG_DIR:-/etc/hydrahive2}/local-media.env"

# Backend und Workflows atomar in die bestehende LLM-Konfiguration eintragen.
# Andere Provider/Defaults bleiben unverändert.
CONFIG_DIR="${HH_CONFIG_DIR:-/etc/hydrahive2}"
LLM_CONFIG="$CONFIG_DIR/llm.json"
export LLM_CONFIG REPO_DIR
python3 - <<'PY'
import json
import os
from pathlib import Path

config_path = Path(os.environ["LLM_CONFIG"])
workflow_dir = Path(os.environ["REPO_DIR"]) / "installer" / "media-workflows"
data = json.loads(config_path.read_text()) if config_path.exists() else {"providers": []}
workflows = [json.loads((workflow_dir / name).read_text()) for name in ("sdxl-image.json", "wan21-t2v.json")]
backend = {
    "id": "local-gpu",
    "name": "Lokale GPU (ComfyUI)",
    "type": "comfyui",
    "api_base": "http://127.0.0.1:8188",
    "workflows": workflows,
}
items = [item for item in data.get("media_backends", []) if item.get("id") != backend["id"]]
data["media_backends"] = [*items, backend]
tmp = config_path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
tmp.replace(config_path)
PY
chown "${HH_USER:-hydrahive}:${HH_USER:-hydrahive}" "$LLM_CONFIG" 2>/dev/null || true
chmod 0640 "$LLM_CONFIG"
log "Local Media Runtime bereit: SDXL-Bild + Wan-Video auf localhost:8188 registriert."
