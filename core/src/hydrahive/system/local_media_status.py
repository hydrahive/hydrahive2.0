"""Status der optionalen lokalen Bild-/Videogenerierung (ComfyUI).

Local Media wird nicht mehr automatisch installiert, sondern im System-Fenster
per Knopf (Entscheidung 26.09.2026). Dieses Modul beantwortet, ob die Runtime
eingerichtet ist und ob eine Installation auf dieser Hardware erlaubt ist.

Die Sperre gilt hart: ohne NVIDIA-GPU, mit zu wenig Grafikspeicher oder zu
wenig freiem Platz ist der Knopf gesperrt, und die API lehnt ab. Dieselben
Grenzwerte prüft installer/modules/72-local-media.sh noch einmal selbst.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from hydrahive.settings import settings

MARKER_NAME = "local-media.enabled"
DEFAULT_MIN_VRAM_MIB = 12_000
# ~33 GB Modelle + ~7 GB ComfyUI-Image + Reserve.
MIN_FREE_BYTES = 40 * 1024**3
DOWNLOAD_BYTES = 33 * 1024**3


def _config_dir() -> Path:
    return settings.config_dir


def _media_root() -> Path:
    return Path(os.environ.get("HH_MEDIA_ROOT", str(settings.data_dir / "local-media")))


def _free_bytes(path: Path) -> int:
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return shutil.disk_usage(probe).free


def _parse_gpus(output: str) -> list[tuple[str, int]]:
    gpus: list[tuple[str, int]] = []
    for line in output.splitlines():
        name, sep, mem = line.rpartition(",")
        if not sep:
            continue
        try:
            gpus.append((name.strip(), int(mem.strip())))
        except ValueError:
            continue
    return gpus


def _query_gpus() -> list[tuple[str, int]] | None:
    """(Name, VRAM in MiB) je NVIDIA-GPU, None ohne nvidia-smi/Treiber."""
    binary = shutil.which("nvidia-smi")
    if not binary:
        return None
    try:
        result = subprocess.run(
            [binary, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return _parse_gpus(result.stdout) or None


def min_vram_mib() -> int:
    try:
        value = int(os.environ.get("HH_MEDIA_MIN_VRAM_MIB", DEFAULT_MIN_VRAM_MIB))
    except ValueError:
        return DEFAULT_MIN_VRAM_MIB
    return value if value > 0 else DEFAULT_MIN_VRAM_MIB


def is_installed() -> bool:
    return (_config_dir() / MARKER_NAME).exists()


def get_status() -> dict:
    installed = is_installed()
    gpus = _query_gpus()
    best = max(gpus, key=lambda g: g[1]) if gpus else None
    free = _free_bytes(_media_root())
    needed_vram = min_vram_mib()

    reason: str | None = None
    if best is None:
        reason = "no_gpu"
    elif best[1] < needed_vram:
        reason = "vram_too_small"
    elif free < MIN_FREE_BYTES:
        reason = "disk_too_small"

    return {
        "installed": installed,
        "can_install": not installed and reason is None,
        "can_uninstall": installed,
        "blocked_reason": reason,
        "gpu": {"name": best[0], "vram_mib": best[1]} if best else None,
        "min_vram_mib": needed_vram,
        "free_bytes": free,
        "min_free_bytes": MIN_FREE_BYTES,
        "download_bytes": DOWNLOAD_BYTES,
    }
