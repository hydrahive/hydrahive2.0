"""/api/files: nur Dateien, die der Nutzer sehen darf (Issue #538, Sicherheitsbefund 10.10.2026).

Vorher bekam jeder angemeldete Nutzer jede Datei unter workspaces/ (alle Projekte, Master, Spezialisten) und /tmp.
Jetzt: Projekt-Workspace nur für Mitglieder (Rolle ≥ read), Master-/Spezialisten-Workspace nur für den Besitzer
(Spezialist eines Projekts auch für dessen Mitglieder), /tmp und unbekannte Ordner nur für System-Admins. Unbekanntes
Projekt/unbekannter Agent → 404 (nicht verraten, ob es ihn gibt). Geprüft wird der aufgelöste Pfad (Symlinks).
"""
from __future__ import annotations

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.agents._paths import workspace_for
from hydrahive.api.middleware import users
from hydrahive.api.middleware.auth import create_token
from hydrahive.projects import config as project_config
from hydrahive.projects._paths import workspace_path
from hydrahive.settings import settings


def _h(name: str) -> dict:
    u = users.get_by_username(name)
    return {"Authorization": f"Bearer {create_token(name, u['role'], u['user_id'])}"}


@pytest.fixture
def world(client):
    """alice (Mitglied von P mit read), bob (kein Mitglied), carol (System-Admin)."""
    made_users = []
    for name, role in (("f_alice", "user"), ("f_bob", "user"), ("f_carol", "admin")):
        users.create(name, "pw-12345678", role)
        made_users.append(name)
    proj = project_config.create(name="Geheim", llm_model="m", created_by="f_carol",
                                 members=[{"username": "f_alice", "role": "read"}])
    ws = workspace_path(proj["id"])
    (ws / "secrets").mkdir(parents=True, exist_ok=True)
    (ws / "secrets" / "akte.txt").write_text("Patientenakte")
    master = agent_config.create(agent_type="master", name="Alices Buddy", llm_model="m", owner="f_alice",
                                 temperature=0.7, max_tokens=1024, thinking_budget=0)
    spec = agent_config.create(agent_type="specialist", name="Projekt-Helfer", llm_model="m", owner="f_carol",
                               temperature=0.7, max_tokens=1024, thinking_budget=0, project_id=proj["id"])
    loose = agent_config.create(agent_type="specialist", name="Bobs Helfer", llm_model="m", owner="f_bob",
                                temperature=0.7, max_tokens=1024, thinking_budget=0)
    files = {}
    for key, agent in (("master", master), ("spec", spec), ("loose", loose)):
        d = workspace_for(agent)
        d.mkdir(parents=True, exist_ok=True)
        (d / "bild.png").write_bytes(b"\x89PNG")
        files[key] = d / "bild.png"
    files["project"] = ws / "secrets" / "akte.txt"
    other = settings.data_dir / "workspaces" / "anderes"
    other.mkdir(parents=True, exist_ok=True)
    (other / "x.txt").write_text("x")
    files["other"] = other / "x.txt"
    tmp = settings.tmp_dir / "hh-files-test.png"
    tmp.write_bytes(b"\x89PNG")
    files["tmp"] = tmp
    yield {"project": proj, "files": files, "master": master, "spec": spec, "loose": loose}
    tmp.unlink(missing_ok=True)
    for a in (master, spec, loose):
        agent_config.delete(a["id"])
    project_config.delete(proj["id"])
    for name in made_users:
        users.delete(name)


def _get(client, path, who, *, query_token=False):
    if query_token:
        u = users.get_by_username(who)
        return client.get("/api/files", params={"path": str(path), "token": create_token(who, u["role"], u["user_id"])})
    return client.get("/api/files", params={"path": str(path)}, headers=_h(who))


# --- Projekt-Workspace -------------------------------------------------------------------------------------------

def test_project_file_for_member_admin_but_not_for_outsider(client, world):
    f = world["files"]["project"]
    assert _get(client, f, "f_alice").status_code == 200
    assert _get(client, f, "f_alice").content == b"Patientenakte"
    assert _get(client, f, "f_carol").status_code == 200
    assert _get(client, f, "f_bob").status_code == 403


def test_query_token_path_is_checked_the_same_way(client, world):
    f = world["files"]["project"]
    assert _get(client, f, "f_bob", query_token=True).status_code == 403
    assert _get(client, f, "f_alice", query_token=True).status_code == 200


def test_unknown_project_is_404_not_403(client, world):
    ghost = settings.data_dir / "workspaces" / "projects" / "019f0000-0000-7000-8000-000000000000"
    ghost.mkdir(parents=True, exist_ok=True)
    (ghost / "a.txt").write_text("a")
    assert _get(client, ghost / "a.txt", "f_bob").status_code == 404
    assert _get(client, ghost / "a.txt", "f_carol").status_code == 200       # Admin darf (Aufräumen, Diagnose)


def test_member_added_later_gets_access_removed_member_loses_it(client, world):
    f, pid = world["files"]["project"], world["project"]["id"]
    project_config.update(pid, members=[{"username": "f_alice", "role": "read"}, {"username": "f_bob", "role": "read"}])
    assert _get(client, f, "f_bob").status_code == 200
    project_config.update(pid, members=[{"username": "f_alice", "role": "read"}])
    assert _get(client, f, "f_bob").status_code == 403


# --- Agent-Workspaces --------------------------------------------------------------------------------------------

def test_master_workspace_only_for_owner_and_admin(client, world):
    f = world["files"]["master"]
    assert _get(client, f, "f_alice").status_code == 200
    assert _get(client, f, "f_bob").status_code == 403
    assert _get(client, f, "f_carol").status_code == 200


def test_project_specialist_workspace_for_project_members(client, world):
    f = world["files"]["spec"]
    assert _get(client, f, "f_alice").status_code == 200       # Mitglied des Projekts des Spezialisten
    assert _get(client, f, "f_bob").status_code == 403


def test_loose_specialist_only_for_owner(client, world):
    f = world["files"]["loose"]
    assert _get(client, f, "f_bob").status_code == 200
    assert _get(client, f, "f_alice").status_code == 403


def test_unknown_agent_workspace_is_404(client, world):
    d = settings.data_dir / "workspaces" / "master" / "gibt-es-nicht-123"
    d.mkdir(parents=True, exist_ok=True)
    (d / "a.png").write_bytes(b"x")
    assert _get(client, d / "a.png", "f_alice").status_code == 404


# --- Sonstiges ---------------------------------------------------------------------------------------------------

def test_other_workspace_folders_and_tmp_only_for_admin(client, world):
    for key in ("other", "tmp"):
        assert _get(client, world["files"][key], "f_alice").status_code == 403, key
        assert _get(client, world["files"][key], "f_carol").status_code == 200, key


def test_symlink_in_own_workspace_to_foreign_project_is_refused(client, world):
    own = workspace_for(world["loose"])
    link = own / "link.txt"
    link.symlink_to(world["files"]["project"])
    assert _get(client, link, "f_bob").status_code == 403
    link.unlink()


def test_dotdot_out_of_own_workspace_is_refused(client, world):
    own = workspace_for(world["loose"])
    sneaky = f"{own}/../../projects/{world['project']['id']}/secrets/akte.txt"
    assert _get(client, sneaky, "f_bob").status_code == 403


def test_outside_all_roots_stays_forbidden_even_for_admin(client, world):
    assert _get(client, settings.data_dir / "sessions.db", "f_carol").status_code == 403
    assert client.get("/api/files", params={"path": "/etc/hostname"}, headers=_h("f_carol")).status_code == 403


def test_without_login_401(client, world):
    assert client.get("/api/files", params={"path": str(world["files"]["project"])}).status_code == 401


def test_stray_files_directly_in_workspace_folders_only_for_admin(client, world):
    """Dateien, die keinem Projekt/Agenten gehören (workspaces/x, workspaces/projects/x) – 403, kein 500/404."""
    root = settings.data_dir / "workspaces"
    for f in (root / "lose.txt", root / "projects" / "lose.txt", root / "master" / "lose.png"):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
        assert _get(client, f, "f_alice").status_code == 403, f
        assert _get(client, f, "f_carol").status_code == 200, f


def test_deeper_files_in_unknown_workspace_folder_only_for_admin(client, world):
    f = settings.data_dir / "workspaces" / "anderes" / "tief" / "x.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x")
    assert _get(client, f, "f_alice").status_code == 403
    assert _get(client, f, "f_carol").status_code == 200


def test_agent_under_wrong_kind_folder_is_404(client, world):
    """Spezialist-ID unter master/ – gehört so niemandem (sonst käme der Besitzer über einen falschen Ordner an Dateien)."""
    d = settings.data_dir / "workspaces" / "master" / world["loose"]["id"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "a.png").write_bytes(b"x")
    assert _get(client, d / "a.png", "f_bob").status_code == 404


def test_media_dirs_stay_readable_for_everyone_logged_in(client, world, tmp_path, monkeypatch):
    media = tmp_path / "medien"
    media.mkdir()
    (media / "film.mp4").write_bytes(b"x")
    monkeypatch.setitem(settings.__dict__, "media_dirs", [media])
    assert _get(client, media / "film.mp4", "f_alice").status_code == 200
    (tmp_path / "daneben.mp4").write_bytes(b"x")
    assert _get(client, tmp_path / "daneben.mp4", "f_alice").status_code == 403    # nur der Medienordner selbst


# --- Folge-Review #539: TOCTOU und HH_MEDIA_DIRS ------------------------------------------------------------------

def test_swap_after_check_does_not_leak_foreign_file(client, world, monkeypatch):
    """Tausch zwischen Prüfung und Öffnen: die geprüfte Datei wird durch einen Symlink auf eine fremde ersetzt.
    Ausgeliefert wird nur, was am geöffneten Handle geprüft ist – also nicht die fremde Akte."""
    from hydrahive.api.routes import files as files_route
    own = workspace_for(world["loose"]) / "harmlos.txt"
    own.write_text("harmlos")
    real_check = files_route.check_read
    swapped = {"done": False}

    def check_then_swap(real, username, role):
        real_check(real, username, role)
        if not swapped["done"] and real == own.resolve():
            swapped["done"] = True
            own.unlink()
            own.symlink_to(world["files"]["project"])       # jetzt zeigt der Name auf alices Akte
    monkeypatch.setattr(files_route, "check_read", check_then_swap)
    r = _get(client, own, "f_bob")
    assert swapped["done"]
    assert r.status_code in (403, 404) and b"Patientenakte" not in r.content


def test_served_from_the_opened_handle_with_ranges(client, world):
    f = world["files"]["project"]
    r = client.get("/api/files", params={"path": str(f)}, headers={**_h("f_alice"), "Range": "bytes=2-5"})
    assert r.status_code == 206 and r.content == b"tien" and r.headers["content-range"] == "bytes 2-5/13"
    r = client.get("/api/files", params={"path": str(f)}, headers=_h("f_alice"))
    assert r.status_code == 200 and r.content == b"Patientenakte" and r.headers["content-length"] == "13"
    assert r.headers["accept-ranges"] == "bytes"


def test_media_dir_containing_data_dir_does_not_open_it(client, world, monkeypatch):
    """HH_MEDIA_DIRS mit data_dir (oder einem Ordner darüber) darf sessions.db & Co. nicht freigeben."""
    db = settings.data_dir / "geheim.db"
    db.write_text("intern")
    for media in (settings.data_dir, settings.data_dir.parent):
        monkeypatch.setitem(settings.__dict__, "media_dirs", [media])
        assert _get(client, db, "f_alice").status_code == 403, media
        assert _get(client, world["files"]["project"], "f_bob").status_code == 403, media   # Workspace-Regel bleibt
    db.unlink()


def test_media_dir_inside_workspace_follows_workspace_rule(client, world, monkeypatch):
    monkeypatch.setitem(settings.__dict__, "media_dirs", [workspace_path(world["project"]["id"])])
    assert _get(client, world["files"]["project"], "f_bob").status_code == 403


@pytest.mark.parametrize("rng, code, body, crange", [
    ("bytes=0-0", 206, b"P", "bytes 0-0/13"),
    ("bytes=10-", 206, b"kte", "bytes 10-12/13"),
    ("bytes=-3", 206, b"kte", "bytes 10-12/13"),
    ("bytes=5-999", 206, b"ntenakte", "bytes 5-12/13"),
    ("bytes=0-1,3-4", 200, b"Patientenakte", None),      # mehrere Bereiche: ganze Datei
    ("bytes=2-3,", 200, b"Patientenakte", None),
    ("kaputt", 200, b"Patientenakte", None),
])
def test_ranges(client, world, rng, code, body, crange):
    r = client.get("/api/files", params={"path": str(world["files"]["project"])}, headers={**_h("f_alice"), "Range": rng})
    assert r.status_code == code and r.content == body and r.headers.get("content-range") == crange


def test_range_beyond_end_is_416(client, world):
    r = client.get("/api/files", params={"path": str(world["files"]["project"])}, headers={**_h("f_alice"), "Range": "bytes=13-"})
    assert r.status_code == 416


def test_directory_and_missing_file_are_404(client, world):
    ws = workspace_path(world["project"]["id"])
    assert _get(client, ws / "secrets", "f_alice").status_code == 404
    assert _get(client, ws / "fehlt.txt", "f_alice").status_code == 404


def test_swap_of_a_parent_folder_after_check_is_caught_at_the_handle(client, world, monkeypatch):
    """Tausch eine Ebene höher: aus dem eigenen Ordner wird ein Symlink auf den fremden Projektordner. Die letzte
    Pfadstelle ist dann kein Symlink (O_NOFOLLOW hilft nicht) – erst die Prüfung am geöffneten Handle fängt es."""
    import shutil

    from hydrahive.api.routes import files as files_route
    own_dir = workspace_for(world["loose"]) / "ordner"
    own_dir.mkdir()
    (own_dir / "akte.txt").write_text("harmlos")
    foreign_dir = world["files"]["project"].parent                 # …/projects/<pid>/secrets mit akte.txt
    real_check = files_route.check_read
    swapped = {"done": False}

    def check_then_swap(real, username, role):
        real_check(real, username, role)
        if not swapped["done"]:
            swapped["done"] = True
            shutil.rmtree(own_dir)
            own_dir.symlink_to(foreign_dir, target_is_directory=True)
    monkeypatch.setattr(files_route, "check_read", check_then_swap)
    r = _get(client, own_dir / "akte.txt", "f_bob")
    assert swapped["done"] and r.status_code == 403 and b"Patientenakte" not in r.content


def test_symlink_as_last_part_is_refused_by_open_itself(tmp_path):
    """O_NOFOLLOW: ein Symlink an letzter Stelle wird nicht geöffnet – auch wenn die Prüfung ihn durchließe."""
    from fastapi import HTTPException

    from hydrahive.api.routes._files_stream import open_checked
    target = tmp_path / "ziel.txt"
    target.write_text("x")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    with pytest.raises(HTTPException) as e:
        open_checked(link, lambda at: None)
    assert e.value.status_code == 403


def test_check_sees_the_real_place_of_the_opened_file(tmp_path):
    from hydrahive.api.routes._files_stream import open_checked
    real_dir = tmp_path / "echt"
    real_dir.mkdir()
    (real_dir / "a.txt").write_text("x")
    (tmp_path / "umweg").symlink_to(real_dir, target_is_directory=True)
    seen = []
    fd, _st = open_checked(tmp_path / "umweg" / "a.txt", seen.append)
    import os
    os.close(fd)
    assert seen == [(real_dir / "a.txt").resolve()]
