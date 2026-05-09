"""Workspace-Permissions: ensure_workspace muss setgid + group-rwx setzen.

Hintergrund: Der Samba-User 'hh' (Mitglied der hydrahive-Gruppe per usermod
im 47-samba.sh) braucht Group-Schreibrechte auf den Projekt-Workspace, sonst
schlagen Save-Operationen über den Share als read-only fehl.

Setgid-Bit (0o2000) sorgt dafür dass Sub-Dirs die hydrahive-Gruppe erben
auch wenn Tools sie unter anderer Default-Group erzeugen würden.
"""
from __future__ import annotations

import os
import stat


def test_ensure_workspace_sets_setgid_and_group_rwx(tmp_path, monkeypatch):
    """Frisch angelegter Workspace bekommt 0o2775 (setgid + rwxrwxr-x)."""
    from hydrahive.projects import _paths
    monkeypatch.setattr(_paths.settings, "data_dir", tmp_path, raising=False)

    p = _paths.ensure_workspace("project-abc")

    assert p.exists()
    mode = p.stat().st_mode & 0o7777
    assert mode == 0o2775, f"Erwartet 0o2775, got 0o{mode:04o}"
    # Setgid-Bit gesetzt
    assert p.stat().st_mode & stat.S_ISGID
    # Group-rwx gesetzt
    assert p.stat().st_mode & stat.S_IRGRP
    assert p.stat().st_mode & stat.S_IWGRP
    assert p.stat().st_mode & stat.S_IXGRP


def test_ensure_workspace_repairs_existing_dir(tmp_path, monkeypatch):
    """Bereits existierende Workspaces ohne Setgid werden nachträglich gefixt."""
    from hydrahive.projects import _paths
    monkeypatch.setattr(_paths.settings, "data_dir", tmp_path, raising=False)

    # Vor-existierenden Workspace mit kaputten Permissions anlegen (default 0o755)
    target = tmp_path / "workspaces" / "projects" / "legacy-vm"
    target.mkdir(parents=True)
    os.chmod(target, 0o755)
    assert target.stat().st_mode & 0o7777 == 0o755

    # ensure_workspace muss die Permissions nachziehen
    p = _paths.ensure_workspace("legacy-vm")
    mode = p.stat().st_mode & 0o7777
    assert mode == 0o2775, f"Erwartet 0o2775 nach Repair, got 0o{mode:04o}"


def test_ensure_workspace_idempotent(tmp_path, monkeypatch):
    """Zweiter Aufruf darf nicht erneut chmod machen wenn Mode schon stimmt.

    Verifizieren wir indirekt: zweiter Aufruf produziert keine Errors und
    der Mode bleibt 0o2775.
    """
    from hydrahive.projects import _paths
    monkeypatch.setattr(_paths.settings, "data_dir", tmp_path, raising=False)

    _paths.ensure_workspace("idem")
    p = _paths.ensure_workspace("idem")
    mode = p.stat().st_mode & 0o7777
    assert mode == 0o2775
