"""Regression: System-Backup MUSS workspaces/ + modules/ enthalten (die echten
Projektdaten), aber VM-Disks (qcow2/vms) ausschließen. Bug: data_subdirs()
listete früher nur agents/projects/plugins/whatsapp → echte Arbeit ging verloren."""
from __future__ import annotations

from pathlib import Path

from hydrahive.backup._paths import data_subdirs, is_excluded


def test_data_subdirs_includes_workspaces_and_modules():
    arcnames = {arc for arc, _ in data_subdirs()}
    assert "data/workspaces" in arcnames, "workspaces/ fehlt im Backup — echte Projektdaten gehen verloren"
    assert "data/modules" in arcnames, "modules/ fehlt im Backup"


def test_workspaces_source_is_the_real_dir(monkeypatch):
    # workspaces_dir muss auf data_dir/workspaces zeigen, NICHT data_dir/projects.
    from hydrahive.settings import settings
    ws = dict(data_subdirs())["data/workspaces"]
    assert ws == settings.data_dir / "workspaces"
    assert ws != settings.projects_dir


def test_vm_disks_excluded():
    # qcow2-Disks und vms/-Verzeichnisse dürfen NIE ins Backup.
    assert is_excluded(Path("data/workspaces/projects/x/vms/disk.qcow2"))
    assert is_excluded(Path("data/workspaces/projects/x/mydisk.qcow2"))
    assert is_excluded(Path("data/workspaces/projects/x/vms"))


def test_normal_workspace_files_included():
    # Normale Projektdateien werden NICHT ausgeschlossen.
    assert not is_excluded(Path("data/workspaces/projects/x/server/main.go"))
    assert not is_excluded(Path("data/modules/videoeditor/backend/routes.py"))
