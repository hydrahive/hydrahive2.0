"""Projekt-Freigabe: Samba-Ordner muss für den Dienst erreichbar sein (Befund WSL 23.11.2026).

Beim Windows-Tester war /etc/samba drwx------ root:root, hh-projects.d darunter drwxrwsr-x. Der Dienst-User kam
nicht durch /etc/samba, die Freigabe meldete „samba_not_installed“, das Cockpit zeigte trotzdem „installiert“.
Nachgestellt in Ubuntu 26.04: install -d -m 2775 /etc/samba/hh-projects.d unter umask 077 → /etc/samba 700.
"""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

from hydrahive.samba import manager
from hydrahive.settings import settings

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "installer" / "lib" / "samba-dirs.sh"
PID = "0123456789abcdef01234567"


def _mode(p: Path) -> int:
    return stat.S_IMODE(p.stat().st_mode)


def _group() -> str:
    import grp
    return grp.getgrgid(os.getgid()).gr_name


# ---------------------------------------------------------------- Installer: Ordner unter strenger umask anlegen

def test_ordner_unter_umask_077_bleibt_fuer_andere_durchgaengig(tmp_path: Path) -> None:
    inc = tmp_path / "etc-samba" / "hh-projects.d"
    subprocess.run(["bash", "-c", 'umask 077; source "$1"; hh_samba_includes_dir "$2" "$3"', "t",
                    str(LIB), str(inc), _group()], check=True)
    assert _mode(inc.parent) & 0o005 == 0o005, oct(_mode(inc.parent))   # andere dürfen durch (r-x)
    assert _mode(inc) == 0o2775


def test_bestehende_rechte_werden_nur_ergaenzt(tmp_path: Path) -> None:
    parent = tmp_path / "etc-samba"
    parent.mkdir(mode=0o700)
    subprocess.run(["bash", "-c", 'source "$1"; hh_samba_includes_dir "$2" "$3"', "t",
                    str(LIB), str(parent / "hh-projects.d"), _group()], check=True)
    assert _mode(parent) == 0o755


def test_alle_wege_nutzen_den_helfer() -> None:
    """Frische Installation, Zusatz-Modul-Knopf und Update gehen alle über hh_samba_includes_dir."""
    for rel in ("installer/modules/50-systemd.sh", "installer/modules/47-samba.sh", "installer/update.sh"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "samba-dirs.sh" in text and "hh_samba_includes_dir" in text, rel
        assert not re.search(r"install -d -m 2775 /etc/samba", text), rel


# ---------------------------------------------------------------- Kern: ehrliche Meldung + ehrlicher Status

@pytest.fixture
def unreachable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """hh-projects.d existiert, aber der Elternordner ist zu (wie /etc/samba 700 für einen fremden User)."""
    parent = tmp_path / "etc-samba"
    inc = parent / "hh-projects.d"
    inc.mkdir(parents=True)
    monkeypatch.setattr(type(settings), "samba_includes_dir", property(lambda self: inc), raising=False)
    monkeypatch.setattr(manager, "is_mac", lambda: False)
    parent.chmod(0o000)
    yield inc
    parent.chmod(0o755)


@pytest.mark.skipif(os.geteuid() == 0, reason="root kommt durch jeden Ordner")
def test_samba_da_aber_ordner_unerreichbar_meldet_kein_zugriff(unreachable, monkeypatch) -> None:
    monkeypatch.setattr(manager, "_find_smbd", lambda: "/usr/sbin/smbd")
    assert manager.enable_share(PID, "P") == (False, "samba_no_access")


@pytest.mark.skipif(os.geteuid() == 0, reason="root kommt durch jeden Ordner")
def test_status_nicht_installiert_solange_ordner_unerreichbar(unreachable, monkeypatch) -> None:
    monkeypatch.setattr(manager, "_find_smbd", lambda: "/usr/sbin/smbd")
    assert manager.samba_status()["installed"] is False


def test_permissionerror_wie_python_312_wird_als_unerreichbar_gewertet(monkeypatch) -> None:
    """Python 3.12 wirft bei zugesperrtem Elternordner PermissionError (CI-Befund #770), 3.14 liefert False."""
    class _Zu(type(Path())):
        def is_dir(self, *a, **k) -> bool:
            raise PermissionError(13, "Permission denied")

        def exists(self, *a, **k) -> bool:
            raise PermissionError(13, "Permission denied")

    zu = _Zu("/etc-samba-zu/hh-projects.d")
    monkeypatch.setattr(type(settings), "samba_includes_dir", property(lambda self: zu), raising=False)
    monkeypatch.setattr(manager, "is_mac", lambda: False)
    monkeypatch.setattr(manager, "_find_smbd", lambda: "/usr/sbin/smbd")
    assert manager.enable_share(PID, "P") == (False, "samba_no_access")
    st = manager.samba_status()
    assert st["installed"] is False and st["includes_dir_exists"] is False


def test_ohne_smbd_bleibt_es_nicht_installiert(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(type(settings), "samba_includes_dir",
                        property(lambda self: tmp_path / "fehlt"), raising=False)
    monkeypatch.setattr(manager, "is_mac", lambda: False)
    monkeypatch.setattr(manager, "_find_smbd", lambda: None)
    assert manager.enable_share(PID, "P") == (False, "samba_not_installed")


def test_alles_da_status_installiert(monkeypatch, tmp_path) -> None:
    inc = tmp_path / "hh-projects.d"
    inc.mkdir()
    monkeypatch.setattr(type(settings), "samba_includes_dir", property(lambda self: inc), raising=False)
    monkeypatch.setattr(manager, "is_mac", lambda: False)
    monkeypatch.setattr(manager, "_find_smbd", lambda: "/usr/sbin/smbd")
    assert manager.samba_status()["installed"] is True


def test_jede_samba_meldung_hat_einen_text() -> None:
    codes = set(re.findall(r'"(samba_[a-z_]+)"', (ROOT / "core/src/hydrahive/samba/manager.py").read_text()))
    codes |= {"samba_failed"}
    assert {"samba_not_installed", "samba_no_access"} <= codes
    for lang in ("de", "en"):
        texts = json.loads((ROOT / f"frontend/src/i18n/locales/{lang}/errors.json").read_text(encoding="utf-8"))
        assert codes <= set(texts), (lang, codes - set(texts))
