"""local-media-ctl.sh und 72-local-media-uninstall.sh wirklich ausführen.

Ersatz-Programme (docker, nvidia-smi) im PATH schreiben ihre Aufrufe mit.
Config-, Daten- und Media-Verzeichnis liegen in tmp_path. So wird das echte
Verhalten geprüft, nicht nur der Skripttext.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
CTL = INSTALLER / "local-media-ctl.sh"
UNINSTALL = INSTALLER / "modules" / "72-local-media-uninstall.sh"
INSTALL = INSTALLER / "modules" / "72-local-media.sh"

FAKE = """#!/usr/bin/env bash
printf '%s %s\\n' "$(basename "$0")" "$*" >> "$FAKE_LOG"
if [ "$(basename "$0")" = nvidia-smi ]; then
  gpu="${FAKE_GPU:-Quadro P2200, 5120}"
  case "$*" in
    *query-gpu=memory.total*) echo "${gpu##*, }" ;;
    *) echo "$gpu" ;;
  esac
fi
exit 0
"""


# Sicherheitsnetz: Auch wenn ein Schutz im Skript fehlt (z. B. bei einer
# Gegenprobe), dürfen rm/du außerhalb des Testordners nichts anfassen.
SAFE_RM = """#!/usr/bin/env bash
for a in "$@"; do
  case "$a" in
    -*) ;;
    "$SANDBOX"/*) ;;
    *) printf 'BLOCKIERT rm %s\\n' "$*" >> "$FAKE_LOG"; exit 99 ;;
  esac
done
exec /bin/rm "$@"
"""
SAFE_DU = """#!/usr/bin/env bash
printf 'du %s\\n' "$*" >> "$FAKE_LOG"
printf '0\\t%s\\n' "${@: -1}"
"""


def _exe(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def box(tmp_path: Path) -> dict:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("docker", "nvidia-smi"):
        _exe(bin_dir / name, FAKE)
    _exe(bin_dir / "rm", SAFE_RM)
    _exe(bin_dir / "du", SAFE_DU)
    cfg, data, media = tmp_path / "etc", tmp_path / "data", tmp_path / "media"
    for d in (cfg, data, media / "models" / "checkpoints", media / "data"):
        d.mkdir(parents=True)
    (media / "models" / "checkpoints" / "sd_xl_base_1.0.safetensors").write_bytes(b"x" * 10)
    (cfg / "llm.json").write_text(json.dumps({
        "providers": [{"id": "openrouter"}],
        "media_backends": [
            {"id": "local-gpu", "type": "comfyui", "api_base": "http://127.0.0.1:8188"},
            {"id": "wks", "type": "comfyui", "api_base": "http://10.0.0.5:8188"},
        ],
        "media_models": {"image": "local:local-gpu/sdxl-image", "video": "google/veo-3.1-fast"},
    }))
    (cfg / "local-media.env").write_text("HH_MEDIA_CONTAINER=hydra-comfyui\n")
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FAKE_LOG": str(tmp_path / "calls.log"),
        "SANDBOX": str(tmp_path),
        "HH_CONFIG_DIR": str(cfg), "HH_DATA_DIR": str(data), "HH_MEDIA_ROOT": str(media),
        "HH_REPO_DIR": str(INSTALLER.parent), "HH_LOCAL_MEDIA_SKIP_ROOT_CHECK": "1",
    }
    return {"env": env, "cfg": cfg, "data": data, "media": media, "tmp": tmp_path}


def _run(script: Path, box: dict, *args: str, **extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(script), *args], env={**box["env"], **extra},
                          capture_output=True, text=True, timeout=60)


def _calls(box: dict) -> str:
    log = box["tmp"] / "calls.log"
    return log.read_text() if log.exists() else ""


# ------------------------------------------------------------ Entfernen

def test_uninstall_removes_container_models_and_backend(box: dict) -> None:
    (box["cfg"] / "local-media.enabled").write_text("1")
    r = _run(UNINSTALL, box)
    assert r.returncode == 0, r.stderr

    assert "docker rm -f hydra-comfyui" in _calls(box)
    assert not box["media"].exists()
    assert not (box["cfg"] / "local-media.env").exists()
    cfg = json.loads((box["cfg"] / "llm.json").read_text())
    assert [b["id"] for b in cfg["media_backends"]] == ["wks"]
    assert cfg["providers"] == [{"id": "openrouter"}]


def test_uninstall_clears_defaults_pointing_to_local_backend(box: dict) -> None:
    _run(UNINSTALL, box)
    models = json.loads((box["cfg"] / "llm.json").read_text())["media_models"]
    assert "image" not in models
    assert models["video"] == "google/veo-3.1-fast"


@pytest.mark.parametrize("root", ["/", "", "relative/path", "/tmp/../"])
def test_uninstall_refuses_dangerous_media_root(box: dict, root: str) -> None:
    r = _run(UNINSTALL, box, HH_MEDIA_ROOT=root)
    assert r.returncode != 0
    assert "docker rm" not in _calls(box)
    assert "BLOCKIERT" not in _calls(box)


def test_uninstall_refuses_unexpected_directory(box: dict, tmp_path: Path) -> None:
    foreign = tmp_path / "foreign"
    (foreign / "wichtig").mkdir(parents=True)
    r = _run(UNINSTALL, box, HH_MEDIA_ROOT=str(foreign))
    assert r.returncode != 0
    assert (foreign / "wichtig").exists()


# ------------------------------------------------------------ Runner

def test_ctl_uninstall_removes_marker_and_consumes_request(box: dict) -> None:
    (box["cfg"] / "local-media.enabled").write_text("1")
    (box["data"] / ".local_media_request").write_text("uninstall")
    r = _run(CTL, box)
    assert r.returncode == 0, r.stderr
    assert not (box["cfg"] / "local-media.enabled").exists()
    assert not (box["data"] / ".local_media_request").exists()
    assert "FERTIG: uninstall ok" in r.stdout


def test_ctl_install_blocked_on_small_gpu_leaves_no_marker(box: dict) -> None:
    (box["data"] / ".local_media_request").write_text("install")
    r = _run(CTL, box, FAKE_GPU="Quadro P2200, 5120")
    assert r.returncode != 0
    assert not (box["cfg"] / "local-media.enabled").exists()
    assert "FEHLER: install" in r.stdout
    assert "docker" not in _calls(box).replace("nvidia-smi", "")


def test_ctl_rejects_unknown_request(box: dict) -> None:
    (box["data"] / ".local_media_request").write_text("rm -rf /")
    r = _run(CTL, box)
    assert r.returncode != 0
    assert "docker" not in _calls(box)
    assert not (box["data"] / ".local_media_request").exists()


def test_ctl_without_request_does_nothing(box: dict) -> None:
    r = _run(CTL, box)
    assert r.returncode == 0
    assert _calls(box) == ""


# ------------------------------------------------------------ Sperre im Installer

def test_installer_blocks_small_gpu_before_docker_and_downloads(box: dict) -> None:
    r = _run(INSTALL, box, FAKE_GPU="Quadro P2200, 5120")
    assert r.returncode != 0
    assert "12000" in r.stderr
    assert "docker" not in _calls(box).replace("nvidia-smi", "")


def test_installer_reports_unreadable_vram_instead_of_silent_exit(box: dict) -> None:
    # set -e + grep ohne Treffer beendete das Skript früher stumm.
    r = _run(INSTALL, box, FAKE_GPU="No devices were found, ?")
    assert r.returncode != 0
    assert "Grafikspeicher nicht ermittelbar" in r.stderr


def test_installer_force_skips_vram_check(box: dict) -> None:
    text = INSTALL.read_text()
    check = text.index("HH_MEDIA_MIN_VRAM_MIB")
    assert 'HH_MEDIA_FORCE' in text[check - 400:check + 800]
