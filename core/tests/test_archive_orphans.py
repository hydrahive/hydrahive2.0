"""Waisen aufräumen (Spec archiv-system.md, Etappe 2b).

Arbeitsordner ohne Agent: leer (oder nur die unveränderte startup.md) → weg, mit Inhalt → Paket.
Agenten, deren Projekt es nicht mehr gibt → normaler Lösch-Auftrag mit Archiv.
"""
from __future__ import annotations

import uuid

import pytest

from tests._delete_fixtures import make_agent, meta, names, packages

pytest_plugins = ["tests._delete_env", "tests._orphan_env"]  # Fixtures `archive_root`, `jobs`


def _ws(kind: str, content: dict[str, str] | None = None) -> tuple[str, object]:
    from hydrahive.settings import settings
    oid = str(uuid.uuid4())
    d = settings.workspaces_dir / kind / oid
    d.mkdir(parents=True)
    for name, text in (content or {}).items():
        (d / name).parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text)
    return oid, d


def _startup_text() -> str:
    from hydrahive.agents.bootstrap import _STARTUP_TEMPLATE
    return _STARTUP_TEMPLATE.read_text(encoding="utf-8")


def test_scan_finds_empty_full_and_ignores_living(archive_root) -> None:
    from hydrahive.archive import orphans
    empty, _ = _ws("specialists")
    startup_only, _ = _ws("master", {"startup.md": _startup_text()})
    full, _ = _ws("specialists", {"ergebnis.md": "wichtig", "sub/daten.csv": "1,2,3"})
    living = make_agent("Lebt noch")

    found = orphans.scan()

    by_id = {w["id"]: w for w in found["workspaces"]}
    assert by_id[empty]["empty"] is True and by_id[startup_only]["empty"] is True
    assert by_id[full]["empty"] is False and by_id[full]["size"] > 0 and by_id[full]["files"] == 2
    assert by_id[startup_only]["kind"] == "master"
    assert living["id"] not in by_id


def test_changed_startup_counts_as_content(archive_root) -> None:
    from hydrahive.archive import orphans
    edited, _ = _ws("master", {"startup.md": _startup_text() + "\nmeine Notiz"})
    assert {w["id"]: w for w in orphans.scan()["workspaces"]}[edited]["empty"] is False


def test_scan_ignores_symlinks_and_bad_names(archive_root, tmp_path) -> None:
    from hydrahive.archive import orphans
    from hydrahive.settings import settings
    outside = tmp_path / "fremd"
    outside.mkdir()
    (outside / "geheim.txt").write_text("x")
    link = settings.workspaces_dir / "specialists" / str(uuid.uuid4())
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside)
    (settings.workspaces_dir / "specialists" / "nicht gültig").mkdir()

    ids = {w["id"] for w in orphans.scan()["workspaces"]}

    assert link.name not in ids and "nicht gültig" not in ids


def test_agent_without_project_is_listed(archive_root) -> None:
    from hydrahive.archive import orphans
    lost = make_agent("Helfer ohne Projekt", project_id=f"weg-{uuid.uuid4().hex[:8]}")
    assert lost["id"] in {a["id"] for a in orphans.scan()["agents"]}


def test_cleanup_removes_empty_and_archives_content(archive_root, jobs) -> None:
    from hydrahive.archive import orphans
    empty, empty_dir = _ws("specialists", {"startup.md": _startup_text()})
    full, full_dir = _ws("specialists", {"ergebnis.md": "wichtiges Ergebnis"})

    orphans.submit_cleanup(workspaces=[empty, full], agents=[], actor="admin")
    jobs.process_queue()

    assert not empty_dir.exists() and not full_dir.exists()
    [pkg] = packages(archive_root, "agents")
    assert "workspace/ergebnis.md" in names(pkg)
    info = meta(pkg)
    assert info["reason"] == "orphan" and info["source_id"] == full
    [job] = jobs.list_jobs()["done"]
    assert job["kind"] == "orphans" and job["state"] == "done"


def test_cleanup_only_touches_listed_ids(archive_root, jobs) -> None:
    from hydrahive.archive import orphans
    listed, listed_dir = _ws("specialists")
    later, later_dir = _ws("specialists", {"neu.md": "kam nach dem Anzeigen"})

    orphans.submit_cleanup(workspaces=[listed], agents=[], actor="admin")
    jobs.process_queue()

    assert not listed_dir.exists() and later_dir.exists()


def test_reassigned_workspace_stays(archive_root, jobs, monkeypatch) -> None:
    """Zwischen Anzeigen und Aufräumen wurde ein Agent mit dieser ID angelegt → bleibt."""
    from hydrahive.agents import config as agent_config
    from hydrahive.archive import orphans
    agent = make_agent("Wieder da")
    ws_dir = orphans.workspace_dir("specialists", agent["id"])
    (ws_dir / "arbeit.md").write_text("gehört dem Agenten")

    orphans.submit_cleanup(workspaces=[agent["id"]], agents=[], actor="admin")
    jobs.process_queue()

    assert (ws_dir / "arbeit.md").exists() and agent_config.get(agent["id"]) is not None
    assert packages(archive_root, "agents") == []


def test_agent_without_project_goes_through_normal_delete(archive_root, jobs) -> None:
    from hydrahive.agents import config as agent_config
    from hydrahive.archive import orphans
    lost = make_agent("Verlorener Helfer", project_id=f"weg-{uuid.uuid4().hex[:8]}")

    orphans.submit_cleanup(workspaces=[], agents=[lost["id"]], actor="admin")
    jobs.process_queue()

    assert agent_config.get(lost["id"]) is None
    [pkg] = packages(archive_root, "agents")
    assert "agent/config.json" in names(pkg) and meta(pkg)["reason"] == "orphan"


def test_agent_that_got_a_project_again_stays(archive_root, jobs) -> None:
    from hydrahive.agents import config as agent_config
    from hydrahive.archive import orphans
    from tests._delete_fixtures import make_project
    project = make_project("Wieder zugeordnet")
    agent = make_agent("Doch nicht verloren", project_id=project["id"])

    orphans.submit_cleanup(workspaces=[], agents=[agent["id"]], actor="admin")
    jobs.process_queue()

    assert agent_config.get(agent["id"]) is not None
    [job] = jobs.list_jobs()["done"]
    assert job["state"] == "failed" and job["error"] == "not_orphan"


def test_restart_mid_cleanup_keeps_finished_and_drops_half(archive_root, jobs, monkeypatch) -> None:
    """Harter Neustart nach dem ersten Ordner: Der erste ist sauber archiviert und weg, der zweite bleibt
    unangetastet, kein halbes Paket."""
    from hydrahive.archive import orphans, package
    first, first_dir = _ws("specialists", {"a.md": "erster"})
    second, second_dir = _ws("specialists", {"b.md": "zweiter"})
    real = package.pack
    calls = {"n": 0}

    class _Crash(BaseException):
        pass

    def crash_on_second(**kw):
        calls["n"] += 1
        if calls["n"] == 2:
            on_target = kw.get("on_target")
            target = archive_root / "agents" / "halb.tar.gz"
            target.parent.mkdir(parents=True, exist_ok=True)
            if on_target:
                on_target(target)
            target.with_name(target.name + ".part").write_bytes(b"halb")
            raise _Crash()
        return real(**kw)

    monkeypatch.setattr(package, "pack", crash_on_second)
    orphans.submit_cleanup(workspaces=[first, second], agents=[], actor="admin")
    with pytest.raises(_Crash):
        jobs.process_queue()

    jobs.recover()

    assert not first_dir.exists() and (second_dir / "b.md").exists()
    left = sorted(p.name for p in (archive_root / "agents").iterdir())
    assert len([n for n in left if n.endswith(".tar.gz")]) == 1 and not any(".part" in n for n in left), left
    [job] = jobs.list_jobs()["done"]
    assert job["state"] == "failed" and job["error"] == "interrupted"


def test_routes(client, admin_headers, auth_headers, archive_root, jobs) -> None:
    from tests.conftest import error_code
    oid, d = _ws("specialists")
    r = client.get("/api/admin/archive/orphans", headers=admin_headers)
    assert r.status_code == 200 and oid in {w["id"] for w in r.json()["workspaces"]}
    assert client.get("/api/admin/archive/orphans", headers=auth_headers).status_code == 403
    r = client.post("/api/admin/archive/orphans/cleanup", headers=admin_headers, json={"workspaces": [], "agents": []})
    assert r.status_code == 400 and error_code(r) == "orphans_nothing_selected"
    r = client.post("/api/admin/archive/orphans/cleanup", headers=admin_headers,
                    json={"workspaces": ["../../etc"], "agents": []})
    assert r.status_code == 400 and error_code(r) == "orphans_invalid_id"
    r = client.post("/api/admin/archive/orphans/cleanup", headers=admin_headers, json={"workspaces": [oid], "agents": []})
    assert r.status_code == 202 and r.json()["job_ids"]
    assert d.exists()                       # nur eingereiht, Reihe läuft in diesem Test nicht


def test_time_budget_never_turns_empty_into_content(archive_root) -> None:
    """Gefunden auf hydratest (kalter Cache): Nach Ablauf des Zeitbudgets galten alle weiteren leeren Ordner als
    „mit Inhalt“. Leer/voll darf nicht vom Budget abhängen – nur die Größe darf „mindestens“ sein."""
    from hydrahive.archive import orphans
    full, _ = _ws("specialists", {"a/b/c.md": "inhalt"})
    empties = [_ws("specialists")[0] for _ in range(3)] + [_ws("master", {"startup.md": _startup_text()})[0]]

    found = {w["id"]: w for w in orphans.orphan_workspaces(budget_s=0)}

    assert all(found[e]["empty"] is True for e in empties)
    assert found[full]["empty"] is False


def test_only_empty_subfolders_count_as_empty(archive_root) -> None:
    from hydrahive.archive import orphans
    oid, d = _ws("specialists")
    (d / "leer" / "auch_leer").mkdir(parents=True)
    assert {w["id"]: w for w in orphans.scan()["workspaces"]}[oid]["empty"] is True


def test_startup_plus_one_more_file_is_content(archive_root) -> None:
    """Unveränderte startup.md + eine weitere Datei (egal in welcher Reihenfolge gelesen) = Inhalt."""
    from hydrahive.archive import orphans
    a, _ = _ws("master", {"startup.md": _startup_text(), "notiz.md": "x"})
    b, _ = _ws("master", {"aaa.md": "x", "startup.md": _startup_text()})
    found = {w["id"]: w for w in orphans.scan()["workspaces"]}
    assert found[a]["empty"] is False and found[b]["empty"] is False


def test_auto_project_links_are_not_content(archive_root, tmp_path) -> None:
    """Buddy-Ordner haben projects/<Name> → Projektordner (von HydraHive angelegt). Nur solche Links = leer.
    Gefunden auf hydratest: 11 Buddy-Waisen wären sonst als Pakete ins Archiv gegangen."""
    from hydrahive.archive import orphans
    from hydrahive.settings import settings
    target = settings.workspaces_dir / "projects" / str(uuid.uuid4())
    target.mkdir(parents=True)
    (target / "projektdatei.md").write_text("gehört dem Projekt")
    oid, d = _ws("master", {"startup.md": _startup_text()})
    (d / "projects").mkdir()
    (d / "projects" / "Mein_Projekt").symlink_to(target)
    (d / "projects" / "Weg").symlink_to(tmp_path / "gibt-es-nicht")
    other, od = _ws("master")
    (od / "projects").mkdir()
    (od / "projects" / "notiz.md").write_text("selbst geschrieben")

    found = {w["id"]: w for w in orphans.scan()["workspaces"]}

    assert found[oid]["empty"] is True and found[other]["empty"] is False


def test_cleanup_never_follows_project_links(archive_root, jobs) -> None:
    from hydrahive.archive import orphans
    from hydrahive.settings import settings
    target = settings.workspaces_dir / "projects" / str(uuid.uuid4())
    target.mkdir(parents=True)
    (target / "projektdatei.md").write_text("gehört dem Projekt")
    oid, d = _ws("master", {"startup.md": _startup_text()})
    (d / "projects").mkdir()
    (d / "projects" / "Mein_Projekt").symlink_to(target)

    orphans.submit_cleanup(workspaces=[oid], agents=[], actor="admin")
    jobs.process_queue()

    assert not d.exists() and (target / "projektdatei.md").exists()


def test_link_to_elsewhere_counts_as_content(archive_root, tmp_path) -> None:
    """Ein Link auf einen fremden, existierenden Ordner ist nicht von HydraHive → Inhalt (wird archiviert)."""
    from hydrahive.archive import orphans
    from hydrahive.settings import settings
    elsewhere = tmp_path / "irgendwo"
    elsewhere.mkdir()
    oid, d = _ws("master")
    (d / "projects").mkdir()
    (d / "projects" / "Fremd").symlink_to(elsewhere)
    top, td = _ws("master")
    (td / "link").symlink_to(elsewhere)
    proj = settings.workspaces_dir / "projects" / str(uuid.uuid4())
    proj.mkdir(parents=True)
    wrong, wd = _ws("master")                                  # Projekt-Link, aber nicht unter projects/
    (wd / "Mein_Projekt").symlink_to(proj)
    found = {w["id"]: w for w in orphans.scan()["workspaces"]}
    assert found[oid]["empty"] is False and found[top]["empty"] is False and found[wrong]["empty"] is False
