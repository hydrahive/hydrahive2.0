"""Tests H6: Auth-Gates für Backup/Restore + RestoreError-Mapping.

Der destruktive System-Replace-Pfad (/api/admin/backup, /restore) hatte keine
Tests. Wichtigstes Loch: dass Nicht-Admins/anonyme Aufrufer abgewiesen werden.
"""
from __future__ import annotations


def test_backup_anonym_401(client):
    resp = client.post("/api/admin/backup")
    assert resp.status_code == 401


def test_backup_nicht_admin_403(client, auth_headers):
    resp = client.post("/api/admin/backup", headers=auth_headers)
    assert resp.status_code == 403


def test_restore_anonym_401(client):
    resp = client.post(
        "/api/admin/restore",
        files={"archive": ("b.tar.gz", b"x", "application/gzip")},
    )
    assert resp.status_code == 401


def test_restore_nicht_admin_403(client, auth_headers):
    resp = client.post(
        "/api/admin/restore",
        files={"archive": ("b.tar.gz", b"x", "application/gzip")},
        headers=auth_headers,
    )
    assert resp.status_code == 403


def test_restore_admin_kaputtes_archiv_400(client, admin_headers):
    """Admin darf rein, aber ein kaputtes (nicht-gzip) Archiv → 400 backup_tar_corrupt."""
    resp = client.post(
        "/api/admin/restore",
        files={"archive": ("b.tar.gz", b"das ist kein gzip-tar", "application/gzip")},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "backup_tar_corrupt"
