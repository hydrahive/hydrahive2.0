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
