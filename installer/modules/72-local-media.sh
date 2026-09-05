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
install -d -m 0755 "$MEDIA_ROOT/data" "$MEDIA_ROOT/models"
log "ComfyUI-Image aktualisieren: $MEDIA_IMAGE"
docker pull "$MEDIA_IMAGE" >/dev/null

docker rm -f hydra-comfyui >/dev/null 2>&1 || true
log "ComfyUI localhost-only starten"
docker run -d --name hydra-comfyui --restart unless-stopped --gpus all \
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
log "Local Media Runtime bereit (localhost:8188; Modelle/Workflows separat konfigurierbar)."
