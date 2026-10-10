"""Verknüpfte Projekte (docs/specs/linked-projects.md): Projekt-Agent und Spezialisten lesen weitere Projekte."""
from __future__ import annotations

import json

import pytest

from hydrahive.agents import config as agent_config
from hydrahive.api.middleware import users
from hydrahive.api.middleware.auth import create_token
from hydrahive.projects import _linked
from hydrahive.projects import config as project_config
from hydrahive.projects._paths import workspace_path
from hydrahive.tools import ToolContext
from hydrahive.tools._path import PathOutsideWorkspace, safe_path


def _h(name: str) -> dict:
    u = users.get_by_username(name)
    return {"Authorization": f"Bearer {create_token(name, u['role'], u['user_id'])}"}


@pytest.fixture
def world(client):
    """VR (Projekt mit Agent + Spezialist), DEV (Quelle). till: Admin in beiden; vr_only: nur VR-Mitglied;
    dev_reader: VR-Admin, in DEV nur read."""
    made = []
    for name, role in (("l_till", "user"), ("l_vronly", "user"), ("l_devread", "user"), ("l_sys", "admin")):
        users.create(name, "pw-12345678", role)
        made.append(name)
    vr = project_config.create(name="HydraVR", llm_model="m", created_by="l_till",
                               members=[{"username": "l_vronly", "role": "write"}, {"username": "l_devread", "role": "admin"}])
    dev = project_config.create(name="Hydrahive DEV", llm_model="m", created_by="l_till",
                                members=[{"username": "l_devread", "role": "read"}])
    other = project_config.create(name="Fremd", llm_model="m", created_by="l_sys")
    ws_dev = workspace_path(dev["id"])
    (ws_dev / "docs").mkdir(parents=True, exist_ok=True)
    (ws_dev / "docs" / "api.md").write_text("HydraHive-API")
    spec = agent_config.create(agent_type="specialist", name="VR-Helfer", llm_model="m", owner="l_till",
                               temperature=0.7, max_tokens=1024, thinking_budget=0, project_id=vr["id"])
    loose = agent_config.create(agent_type="specialist", name="Loser Helfer", llm_model="m", owner="l_till",
                                temperature=0.7, max_tokens=1024, thinking_budget=0)
    yield {"vr": vr, "dev": dev, "other": other, "spec": spec, "loose": loose, "file": ws_dev / "docs" / "api.md"}
    for a in (spec, loose):
        agent_config.delete(a["id"])
    for p in (vr, dev, other):
        project_config.delete(p["id"])
    for name in made:
        users.delete(name)


# --- Einstellen ---------------------------------------------------------------------------------------------------

def test_set_and_read_links(world):
    vr, dev = world["vr"], world["dev"]
    out = _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    assert out == [dev["id"]] and project_config.get(vr["id"])["linked_projects"] == [dev["id"]]
    assert _linked.set_links(vr["id"], [], username="l_till", role="user") == []


def test_linking_needs_admin_here_and_write_there(world):
    vr, dev, other = world["vr"], world["dev"], world["other"]
    with pytest.raises(_linked.LinkError) as e:
        _linked.set_links(vr["id"], [dev["id"]], username="l_vronly", role="user")      # in VR nur write
    assert e.value.code == "project_admin_required"
    with pytest.raises(_linked.LinkError) as e:
        _linked.set_links(vr["id"], [dev["id"]], username="l_devread", role="user")     # in DEV nur read
    assert e.value.code == "linked_project_no_access" and e.value.project == dev["id"]
    with pytest.raises(_linked.LinkError):
        _linked.set_links(vr["id"], [other["id"]], username="l_till", role="user")      # gar kein Mitglied
    assert _linked.set_links(vr["id"], [other["id"]], username="l_sys", role="admin") == [other["id"]]


@pytest.mark.parametrize("bad", ["self", "unknown", "dup", "notlist", "tolong"])
def test_invalid_lists_are_rejected(world, bad):
    vr, dev = world["vr"], world["dev"]
    value = {"self": [vr["id"]], "unknown": ["019f0000-0000-7000-8000-000000000000"], "dup": [dev["id"], dev["id"]],
             "notlist": dev["id"], "tolong": [dev["id"]] * (_linked.MAX_LINKS + 1)}[bad]
    with pytest.raises(_linked.LinkError) as e:
        _linked.set_links(vr["id"], value, username="l_sys", role="admin")
    assert e.value.code == "linked_projects_invalid"
    assert project_config.get(vr["id"]).get("linked_projects", []) == []


# --- Wirksam im Lauf ----------------------------------------------------------------------------------------------

def test_effective_for_project_agent_and_project_specialist_only(world):
    vr, dev = world["vr"], world["dev"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    project_agent = agent_config.get(project_config.get(vr["id"])["agent_id"])
    assert _linked.effective(project_agent, vr["id"], "l_till") == [dev["id"]]
    assert _linked.effective(world["spec"], vr["id"], "l_till") == [dev["id"]]
    assert _linked.effective(world["loose"], vr["id"], "l_till") == []           # gehört nicht zum Projekt
    assert _linked.effective(project_agent, None, "l_till") == []


def test_only_if_the_user_of_the_run_is_member_there(world):
    vr, dev = world["vr"], world["dev"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    agent = agent_config.get(project_config.get(vr["id"])["agent_id"])
    assert _linked.effective(agent, vr["id"], "l_vronly") == []                  # kein Mitglied von DEV
    assert _linked.effective(agent, vr["id"], "l_devread") == [dev["id"]]        # read reicht zum Lesen
    assert _linked.effective(agent, vr["id"], "l_sys") == [dev["id"]]            # System-Admin


def test_deleted_linked_project_is_ignored(world):
    vr, dev = world["vr"], world["dev"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    agent = agent_config.get(project_config.get(vr["id"])["agent_id"])
    project_config.delete(dev["id"])
    assert _linked.effective(agent, vr["id"], "l_till") == []


# --- Dateien: nur lesen -------------------------------------------------------------------------------------------

def _ctx(agent, project_id, user):
    return ToolContext(session_id="s", agent_id=agent["id"], user_id=user, workspace=workspace_path(project_id),
                       project_id=project_id)


def test_read_path_allows_linked_workspace_but_write_does_not(world):
    vr, dev = world["vr"], world["dev"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    agent = agent_config.get(project_config.get(vr["id"])["agent_id"])
    ctx = _ctx(agent, vr["id"], "l_till")
    assert _linked.read_path(ctx, str(world["file"])) == world["file"].resolve()
    with pytest.raises(PathOutsideWorkspace):
        safe_path(ctx.workspace, str(world["file"]))                            # Schreib-Weg bleibt zu
    with pytest.raises(PathOutsideWorkspace):
        _linked.read_path(_ctx(agent, vr["id"], "l_vronly"), str(world["file"]))  # Nutzer kein DEV-Mitglied
    other_file = workspace_path(world["other"]["id"]) / "x.txt"
    other_file.parent.mkdir(parents=True, exist_ok=True)
    other_file.write_text("x")
    with pytest.raises(PathOutsideWorkspace):
        _linked.read_path(ctx, str(other_file))                                 # nicht verknüpft


def test_linked_folder_in_own_workspace_points_to_the_project(world):
    vr, dev = world["vr"], world["dev"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    link = workspace_path(vr["id"]) / "linked" / "Hydrahive_DEV"
    assert link.is_symlink() and link.resolve() == workspace_path(dev["id"]).resolve()
    agent = agent_config.get(project_config.get(vr["id"])["agent_id"])
    assert _linked.read_path(_ctx(agent, vr["id"], "l_till"), "linked/Hydrahive_DEV/docs/api.md") == world["file"].resolve()
    _linked.set_links(vr["id"], [], username="l_till", role="user")
    assert not link.exists() and not link.is_symlink()


async def test_file_read_tool_reads_linked_file_and_file_write_refuses(world):
    from hydrahive.tools import file_read, file_write
    vr, dev = world["vr"], world["dev"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    agent = agent_config.get(project_config.get(vr["id"])["agent_id"])
    ctx = _ctx(agent, vr["id"], "l_till")
    res = await file_read.TOOL.execute({"path": str(world["file"])}, ctx)
    assert res.success and "HydraHive-API" in str(res.output)
    res = await file_write.TOOL.execute({"path": str(world["file"]), "content": "kaputt"}, ctx)
    assert not res.success and world["file"].read_text() == "HydraHive-API"
    res = await file_read.TOOL.execute({"path": str(world["file"])}, _ctx(agent, vr["id"], "l_vronly"))
    assert not res.success


# --- Wissen + Hinweis ---------------------------------------------------------------------------------------------

def test_datamining_scope_includes_effective_links(world):
    from hydrahive.db._mirror_scope import scope_for
    vr, dev = world["vr"], world["dev"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    agent = agent_config.get(project_config.get(vr["id"])["agent_id"])
    assert scope_for(agent, username="l_till", project_id=vr["id"]).projects == (vr["id"], dev["id"])
    assert scope_for(agent, username="l_vronly", project_id=vr["id"]).projects == (vr["id"],)


def test_layout_hint_names_linked_projects(world):
    from hydrahive.runner._run_workspace import project_layout_hint
    vr, dev = world["vr"], world["dev"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    agent = agent_config.get(project_config.get(vr["id"])["agent_id"])
    hint = project_layout_hint(workspace_path(vr["id"]), project_config.get(vr["id"]), agent=agent, username="l_till")
    assert "Verknüpfte Projekte (nur lesen)" in hint and "Hydrahive DEV" in hint and "linked/Hydrahive_DEV" in hint
    hint = project_layout_hint(workspace_path(vr["id"]), project_config.get(vr["id"]), agent=agent, username="l_vronly")
    assert "Verknüpfte Projekte" not in hint


# --- Route --------------------------------------------------------------------------------------------------------

def test_route_sets_links_with_rights_and_audit(client, world):
    vr, dev = world["vr"], world["dev"]
    url = f"/api/projects/{vr['id']}/linked-projects"
    r = client.put(url, json={"projects": [dev["id"]]}, headers=_h("l_vronly"))
    assert r.status_code == 403
    r = client.put(url, json={"projects": [dev["id"]]}, headers=_h("l_till"))
    assert r.status_code == 200 and r.json()["linked_projects"] == [dev["id"]]
    r = client.put(url, json={"projects": ["019f0000-0000-7000-8000-000000000000"]}, headers=_h("l_till"))
    assert r.status_code == 400
    got = client.get(f"/api/projects/{vr['id']}", headers=_h("l_till")).json()
    assert got["linked_projects"] == [dev["id"]]
    from hydrahive.projects import audit as project_audit
    events = project_audit.list_for_project(vr["id"], action="linked_projects_changed")
    assert events and events[0]["user"] == "l_till"
    assert dev["id"] in json.dumps(events[0])


def test_read_path_is_offered_in_tools_path_for_plugins(world):
    """Plugins (grep/find/tree) importieren hydrahive.tools._path.read_path – gleiche Regeln."""
    from hydrahive.tools._path import read_path
    vr, dev = world["vr"], world["dev"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    agent = agent_config.get(project_config.get(vr["id"])["agent_id"])
    assert read_path(_ctx(agent, vr["id"], "l_till"), str(world["file"])) == world["file"].resolve()
    with pytest.raises(PathOutsideWorkspace):
        read_path(_ctx(agent, vr["id"], "l_vronly"), str(world["file"]))


def test_symlink_in_own_workspace_to_unlinked_project_stays_closed(world):
    vr, dev, other = world["vr"], world["dev"], world["other"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    agent = agent_config.get(project_config.get(vr["id"])["agent_id"])
    secret = workspace_path(other["id"]) / "geheim.txt"
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_text("x")
    (workspace_path(vr["id"]) / "trick").symlink_to(workspace_path(other["id"]), target_is_directory=True)
    with pytest.raises(PathOutsideWorkspace):
        _linked.read_path(_ctx(agent, vr["id"], "l_till"), "trick/geheim.txt")
    with pytest.raises(PathOutsideWorkspace):
        _linked.read_path(_ctx(agent, vr["id"], "l_till"), f"linked/Hydrahive_DEV/../../{other['id']}/geheim.txt")


def test_project_rename_and_delete_keep_link_dir_in_sync(world):
    vr, dev = world["vr"], world["dev"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    project_config.update(dev["id"], name="DEV neu")
    assert (workspace_path(vr["id"]) / "linked" / "DEV_neu").is_symlink()
    assert not (workspace_path(vr["id"]) / "linked" / "Hydrahive_DEV").exists()
    project_config.delete(dev["id"])
    assert not any((workspace_path(vr["id"]) / "linked").iterdir())


def test_neighbour_folder_with_same_prefix_is_not_readable(world):
    """…/projects/<dev-id>-alt neben …/projects/<dev-id> gehört nicht zum verknüpften Projekt."""
    vr, dev = world["vr"], world["dev"]
    _linked.set_links(vr["id"], [dev["id"]], username="l_till", role="user")
    agent = agent_config.get(project_config.get(vr["id"])["agent_id"])
    neighbour = workspace_path(dev["id"]).parent / f"{dev['id']}-alt"
    neighbour.mkdir(parents=True, exist_ok=True)
    (neighbour / "x.txt").write_text("x")
    with pytest.raises(PathOutsideWorkspace):
        _linked.read_path(_ctx(agent, vr["id"], "l_till"), str(neighbour / "x.txt"))
