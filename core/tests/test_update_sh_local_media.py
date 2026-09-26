"""update.sh: Local Media nur noch mit Marker, bestehende Installationen bleiben an.

Bug-Kontext 26.09.2026: Nach dem Einbau einer Quadro P2200 (5 GB) hat das
reguläre Update ungefragt ~33 GB Modelle geladen und ComfyUI gestartet, weil
72-local-media.sh nur `command -v nvidia-smi` prüfte. Außerdem brach ein
fehlgeschlagener Download das gesamte Update ab (err -> exit 1), noch vor
Frontend-Build und Neustart.

Der relevante update.sh-Block wird ausgeschnitten und wirklich ausgeführt,
mit Ersatz für docker und 72-local-media.sh.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
UPDATE = INSTALLER / "update.sh"
BEGIN = "# --- Local Media (Opt-in) ---"
END = "# --- Local Media Ende ---"


def _block() -> str:
    text = UPDATE.read_text()
    return text[text.index(BEGIN):text.index(END)]


@pytest.fixture
def box(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    (repo / "installer" / "modules").mkdir(parents=True)
    module = repo / "installer" / "modules" / "72-local-media.sh"
    module.write_text('#!/usr/bin/env bash\necho ran >> "$CALLS"\nexit "${FAKE_MODULE_RC:-0}"\n')
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text('#!/usr/bin/env bash\n'
                      'if [ "$1 $2" = "container inspect" ] && [ "${FAKE_CONTAINER:-0}" = 1 ]; then exit 0; fi\n'
                      'exit 1\n')
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
    cfg = tmp_path / "etc"
    cfg.mkdir()
    script = tmp_path / "block.sh"
    script.write_text(
        "set -euo pipefail\n"
        'log() { echo "LOG $*"; }\n'
        'err() { echo "ERR $*"; exit 1; }\n'
        + _block()
        + 'echo "UPDATE-LAEUFT-WEITER"\n'
    )
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "CALLS": str(tmp_path / "calls"),
           "HH_REPO_DIR": str(repo), "HH_CONFIG_DIR": str(cfg)}
    return {"script": script, "env": env, "cfg": cfg, "calls": tmp_path / "calls"}


def _run(box: dict, **extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(box["script"])], env={**box["env"], **extra},
                          capture_output=True, text=True, timeout=30)


def test_without_marker_and_container_nothing_is_installed(box: dict) -> None:
    r = _run(box)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not box["calls"].exists(), "72-local-media.sh darf ohne Opt-in nicht laufen"
    assert not (box["cfg"] / "local-media.enabled").exists()


def test_existing_container_is_migrated_to_enabled(box: dict) -> None:
    r = _run(box, FAKE_CONTAINER="1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (box["cfg"] / "local-media.enabled").exists()
    assert box["calls"].read_text() == "ran\n"


def test_marker_keeps_runtime_updated(box: dict) -> None:
    (box["cfg"] / "local-media.enabled").write_text("1")
    _run(box)
    assert box["calls"].read_text() == "ran\n"


def test_failing_module_does_not_abort_update(box: dict) -> None:
    (box["cfg"] / "local-media.enabled").write_text("1")
    r = _run(box, FAKE_MODULE_RC="1")
    assert r.returncode == 0
    assert "UPDATE-LAEUFT-WEITER" in r.stdout
    assert "ERR" not in r.stdout


def test_update_never_calls_module_unconditionally() -> None:
    text = UPDATE.read_text()
    outside = text.replace(_block(), "")
    assert "72-local-media.sh" not in outside


def test_update_installs_local_media_trigger_units() -> None:
    text = UPDATE.read_text()
    assert "hydrahive2-local-media.service" in text
    assert "hydrahive2-local-media.timer" in text
    assert "installer/local-media-ctl.sh" in text
    unit = text[text.index("hydrahive2-local-media.service <<EOF"):]
    unit = unit[:unit.index("\nEOF")]
    assert "ExecStartPre" not in unit, "Anfrage muss liegen bleiben, bis local-media-ctl.sh fertig ist"
    assert re.search(r"TimeoutStartSec=0", unit)
