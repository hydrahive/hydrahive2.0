"""Status und Sperre der lokalen Bild-/Videogenerierung (ComfyUI).

Entscheidung Till (26.09.2026): Die Installation wird bei zu kleiner oder
fehlender Grafikkarte gesperrt, nicht nur gewarnt. Anlass war eine Quadro
P2200 (5 GB), auf die das Update ungefragt 33 GB Modelle geladen hat.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.system import local_media_status as lms

GIB = 1024**3


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(lms, "_config_dir", lambda: tmp_path / "etc")
    monkeypatch.setattr(lms, "_media_root", lambda: tmp_path / "media")
    monkeypatch.setattr(lms, "_free_bytes", lambda _p: 400 * GIB)
    monkeypatch.delenv("HH_MEDIA_MIN_VRAM_MIB", raising=False)
    (tmp_path / "etc").mkdir()
    return tmp_path


def _gpu(monkeypatch: pytest.MonkeyPatch, gpus: list[tuple[str, int]] | None) -> None:
    monkeypatch.setattr(lms, "_query_gpus", lambda: gpus)


def test_no_nvidia_gpu_blocks_install(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _gpu(monkeypatch, None)
    st = lms.get_status()
    assert st["installed"] is False
    assert st["can_install"] is False
    assert st["blocked_reason"] == "no_gpu"


def test_small_gpu_blocks_install(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _gpu(monkeypatch, [("Quadro P2200", 5120)])
    st = lms.get_status()
    assert st["can_install"] is False
    assert st["blocked_reason"] == "vram_too_small"
    assert st["gpu"] == {"name": "Quadro P2200", "vram_mib": 5120}
    assert st["min_vram_mib"] == 12000


def test_large_gpu_allows_install(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _gpu(monkeypatch, [("NVIDIA GeForce RTX 5060 Ti", 16311)])
    st = lms.get_status()
    assert st["can_install"] is True
    assert st["blocked_reason"] is None


def test_best_gpu_counts_when_several(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _gpu(monkeypatch, [("Quadro P2200", 5120), ("RTX 4090", 24564)])
    st = lms.get_status()
    assert st["gpu"]["name"] == "RTX 4090"
    assert st["can_install"] is True


def test_not_enough_disk_blocks_install(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _gpu(monkeypatch, [("RTX 5060 Ti", 16311)])
    monkeypatch.setattr(lms, "_free_bytes", lambda _p: 20 * GIB)
    st = lms.get_status()
    assert st["can_install"] is False
    assert st["blocked_reason"] == "disk_too_small"


def test_min_vram_can_be_overridden(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _gpu(monkeypatch, [("Quadro P2200", 5120)])
    monkeypatch.setenv("HH_MEDIA_MIN_VRAM_MIB", "4000")
    assert lms.get_status()["can_install"] is True


def test_invalid_min_vram_falls_back_to_default(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _gpu(monkeypatch, [("Quadro P2200", 5120)])
    monkeypatch.setenv("HH_MEDIA_MIN_VRAM_MIB", "abc")
    assert lms.get_status()["min_vram_mib"] == 12000


def test_marker_means_installed_even_on_small_gpu(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # HydrahiveHome: eingerichtet, obwohl die Karte zu klein ist. Entfernen muss möglich sein.
    _gpu(monkeypatch, [("Quadro P2200", 5120)])
    (env / "etc" / "local-media.enabled").write_text("1")
    st = lms.get_status()
    assert st["installed"] is True
    assert st["can_uninstall"] is True


def test_not_installed_cannot_uninstall(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _gpu(monkeypatch, [("RTX 5060 Ti", 16311)])
    assert lms.get_status()["can_uninstall"] is False


def test_parse_nvidia_smi_output() -> None:
    out = "Quadro P2200, 5120\nNVIDIA GeForce RTX 5060 Ti, 16311\n\n"
    assert lms._parse_gpus(out) == [("Quadro P2200", 5120), ("NVIDIA GeForce RTX 5060 Ti", 16311)]


def test_parse_ignores_garbage_lines() -> None:
    assert lms._parse_gpus("No devices were found\n") == []
