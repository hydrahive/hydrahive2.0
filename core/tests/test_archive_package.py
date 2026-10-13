"""Archiv-Pakete bauen (Spec docs/specs/archiv-system.md, Etappe 1).

Ein Paket ist `<zeit>_<name>_<id8>.tar.gz` plus `.json` daneben. Es muss
vollständig sein, bevor es seinen Endnamen bekommt. Abgebrochenes Packen
darf kein halbes Paket zurücklassen (das Löschen in Etappe 2 verlässt sich
darauf).
"""
from __future__ import annotations

import hashlib
import json
import os
import tarfile
from pathlib import Path

import pytest

from hydrahive.archive import package
from hydrahive.archive._paths import archive_root
from hydrahive.settings import settings


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    from hydrahive.archive import location
    r = tmp_path / "archiv"
    monkeypatch.setattr(location, "archive_root", lambda: r)
    return r


@pytest.fixture
def src(tmp_path) -> Path:
    s = tmp_path / "quelle"
    (s / "sub").mkdir(parents=True)
    (s / "a.txt").write_text("hallo")
    (s / "sub" / "b.md").write_text("# Notiz")
    return s


def _names(tgz: Path) -> set[str]:
    with tarfile.open(tgz) as tar:
        return set(tar.getnames())


def test_root_follows_location(root: Path) -> None:
    assert archive_root() == root


def test_pack_writes_tar_json_and_checksum(root: Path, src: Path) -> None:
    entry = package.pack(
        kind="agents", name="Mein Agent", source_id="0450556d-37ef-41d0",
        owner="till", reason="agent_deleted", sources=[("workspace", src)],
        extra={"type": "specialist"},
    )

    tgz = root / "agents" / entry["file"]
    assert tgz.is_file() and tgz.name.endswith(".tar.gz")
    assert {"workspace/a.txt", "workspace/sub/b.md"} <= _names(tgz)
    meta = json.loads((root / "agents" / (entry["file"] + ".json")).read_text())
    assert meta["kind"] == "agents" and meta["name"] == "Mein Agent"
    assert meta["source_id"] == "0450556d-37ef-41d0" and meta["owner"] == "till"
    assert meta["reason"] == "agent_deleted" and meta["extra"] == {"type": "specialist"}
    assert meta["size"] == tgz.stat().st_size
    assert meta["sha256"] == hashlib.sha256(tgz.read_bytes()).hexdigest()
    assert meta["created_at"].endswith("Z")
    assert not list(root.rglob("*.part"))


def test_file_name_is_safe_and_sortable(root: Path, src: Path) -> None:
    entry = package.pack(kind="projects", name="../../etc/Böse Name; rm -rf",
                         source_id="019e953f-aa74-78e4", owner="till", reason="x",
                         sources=[("p", src)])

    name = entry["file"]
    assert "/" not in name and ".." not in name and " " not in name and ";" not in name
    assert name[:4].isdigit() and name.endswith("_019e953f.tar.gz")
    assert (root / "projects" / name).is_file()


def test_unknown_kind_rejected(root: Path, src: Path) -> None:
    with pytest.raises(ValueError):
        package.pack(kind="../etc", name="x", source_id="1", owner="o", reason="r", sources=[("a", src)])


def test_mounts_are_never_packed(root: Path, src: Path, monkeypatch) -> None:
    """Eingehängte Laufwerke (z. B. mounts/Hydrahive_backups) gehören nicht ins Paket."""
    mnt = src / "mounts" / "nas"
    mnt.mkdir(parents=True)
    (mnt / "riesig.bin").write_text("x")
    real = os.path.ismount
    monkeypatch.setattr(package.os.path, "ismount", lambda p: str(p) == str(mnt) or real(p))

    entry = package.pack(kind="projects", name="p", source_id="1", owner="o", reason="r", sources=[("ws", src)])

    names = _names(root / "projects" / entry["file"])
    assert "ws/a.txt" in names
    assert not any("riesig.bin" in n for n in names)


def test_everything_of_the_source_is_kept(root: Path, tmp_path: Path) -> None:
    """Archiv ≠ System-Backup: Was der Nutzer hatte, kommt komplett mit – auch
    VM-Platten (.qcow2) und Ordner namens vms/tls (System-Backup lässt die weg).
    Auch ein Elternordner mit solchem Namen darf nichts ausschließen."""
    src = tmp_path / "vms" / "projekt"
    (src / "tls").mkdir(parents=True)
    (src / "tls" / "cert.pem").write_text("c")
    (src / "disk.qcow2").write_text("d")
    (src / ".plugin-cache").mkdir()
    (src / ".plugin-cache" / "x").write_text("x")

    entry = package.pack(kind="projects", name="p", source_id="1", owner="o", reason="r", sources=[("ws", src)])

    assert {"ws/tls/cert.pem", "ws/disk.qcow2", "ws/.plugin-cache/x"} <= _names(root / "projects" / entry["file"])


def test_symlinks_stay_symlinks(root: Path, src: Path, tmp_path: Path) -> None:
    """Agent-Ordner enthalten Symlinks (master/<id>/projects/…). Nicht folgen."""
    outside = tmp_path / "draussen"
    outside.mkdir()
    (outside / "geheim.txt").write_text("nicht einpacken")
    (src / "link").symlink_to(outside)

    entry = package.pack(kind="agents", name="a", source_id="1", owner="o", reason="r", sources=[("ws", src)])

    with tarfile.open(root / "agents" / entry["file"]) as tar:
        info = tar.getmember("ws/link")
        assert info.issym() and info.linkname == str(outside)
        assert not any("geheim.txt" in n for n in tar.getnames())


def test_missing_source_is_skipped(root: Path, src: Path, tmp_path: Path) -> None:
    entry = package.pack(kind="agents", name="a", source_id="1", owner="o", reason="r",
                         sources=[("agent", tmp_path / "gibt-es-nicht"), ("ws", src)])

    assert "ws/a.txt" in _names(root / "agents" / entry["file"])


def test_failed_packing_leaves_nothing(root: Path, src: Path, monkeypatch) -> None:
    def boom(*a, **k):
        raise OSError("Platte voll")

    monkeypatch.setattr(package.tarfile.TarFile, "addfile", boom)

    with pytest.raises(OSError):
        package.pack(kind="agents", name="a", source_id="1", owner="o", reason="r", sources=[("ws", src)])

    leftovers = [p for p in root.rglob("*") if p.is_file()]
    assert leftovers == []


def test_two_packs_same_second_do_not_collide(root: Path, src: Path) -> None:
    a = package.pack(kind="agents", name="a", source_id="11111111", owner="o", reason="r", sources=[("ws", src)])
    b = package.pack(kind="agents", name="a", source_id="11111111", owner="o", reason="r", sources=[("ws", src)])

    assert a["file"] != b["file"]
    assert len(list((root / "agents").glob("*.tar.gz"))) == 2


def test_subfolders_skip_and_entries(root: Path, src: Path) -> None:
    """Etappe 2: Projekt-Pakete haben agents/<id>/agent; ersetzte Dateien (config mit ***) werden übersprungen."""
    seen: list[int] = []
    entry = package.pack(kind="projects", name="p", source_id="1", owner="o", reason="r",
                         sources=[("agents/abc/agent", src), ("../../böse/../x", src)],
                         skip={"agents/abc/agent/a.txt"}, on_file=seen.append)

    names = _names(root / "projects" / entry["file"])
    assert "agents/abc/agent/sub/b.md" in names and "agents/abc/agent/a.txt" not in names
    assert not any(n.startswith("/") or ".." in n.split("/") for n in names)
    assert entry["entries"] == len(names) and sum(seen) > 0
