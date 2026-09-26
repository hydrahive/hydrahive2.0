#!/bin/sh
# Idempotente GPU-Runtime für Compute-Nodes. Wird aus setup.sh aufgerufen.
set -eu

log() { printf '[hydrahive-media] %s\n' "$*"; }
[ "$(id -u)" -eq 0 ] || { echo 'Als root ausführen.' >&2; exit 1; }
command -v nvidia-smi >/dev/null 2>&1 || { log 'Keine NVIDIA-GPU — übersprungen.'; exit 0; }
command -v apt-get >/dev/null 2>&1 || { echo 'apt-get fehlt.' >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive

if ! command -v docker >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq docker.io
    systemctl enable --now docker
fi
if ! command -v nvidia-ctk >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq curl ca-certificates gpg
    install -d -m 0755 /usr/share/keyrings
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey |
        gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list |
        sed 's#^deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#' \
        > /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update -qq
    apt-get install -y -qq nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker
fi

docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi >/dev/null 2>&1 || {
    echo 'NVIDIA-Docker-Runtime funktioniert nicht.' >&2; exit 1;
}
ROOT=${HH_MEDIA_ROOT:-/var/lib/hydrahive2/local-media}
IMAGE=${HH_MEDIA_IMAGE:-yanwk/comfyui-boot:cu128-slim}
install -d -m 0755 "$ROOT/data" "$ROOT/models"
docker pull "$IMAGE" >/dev/null
docker rm -f hydra-comfyui >/dev/null 2>&1 || true
docker run -d --name hydra-comfyui --restart unless-stopped --gpus all \
    -p 127.0.0.1:8188:8188 \
    -v "$ROOT/data:/root/ComfyUI" -v "$ROOT/models:/root/ComfyUI/models" \
    "$IMAGE" >/dev/null
log 'ComfyUI lokal auf 127.0.0.1:8188 gestartet.'
