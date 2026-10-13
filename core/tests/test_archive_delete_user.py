"""Nutzer löschen: alles am Namen weg, eigene Projekte als eigene Pakete; Fehler 2 (Spec archiv-system.md, Etappe 2)."""
from __future__ import annotations

import json
import uuid

import pytest

from hydrahive.archive import deletion
from tests._delete_fixtures import (
    make_agent, make_chat, make_project, meta, names, packages, read_member, session_exists,
)

pytest_plugins = ["tests._delete_fixtures"]  # Fixture `archive_root`


@pytest.fixture
def victim():
    """Nutzer „opfer“ mit allem, was am Namen hängt."""
    from hydrahive.api.middleware import api_keys, users
    from hydrahive.butler import persistence as bp
    from hydrahive.butler.models import Flow
    from hydrahive.communication.discord import config as discord_config
    from hydrahive.communication.whatsapp import config as wa_config
    from hydrahive.credentials import store as cred_store
    from hydrahive.credentials.models import Credential
    from hydrahive.db import user_preferences
    from hydrahive.schedules import db as sched_db
    from hydrahive.skills._paths import user_dir
    name = f"opfer{uuid.uuid4().hex[:6]}"      # eigener Name je Test: die Test-DB lebt die ganze Sitzung
    uid = users.create(name, "testpass123", role="user")
    api_keys.create(name="k", username=name, role="user", user_id=uid)
    own = make_project("Eigenes Projekt", created_by=name, members=[name])
    foreign = make_project("Fremdes Projekt", created_by="testuser",
                           members=["testuser", {"username": name, "role": "admin"}])
    agent = make_agent("Agent von opfer", owner=name, agent_type="master")
    in_foreign = make_agent("Helfer im fremden Projekt", owner=name, project_id=foreign["id"])
    chat = make_chat(agent["id"], user=name, text="private Frage")
    foreign_chat = make_chat(in_foreign["id"], user=name, project_id=foreign["id"], text="im fremden Projekt")
    cred_store.save_credential(name, Credential(name="nas", type="basic", value="nas-geheim-passwort",
                                                url_pattern="https://nas.local/*"))
    user_dir(name).mkdir(parents=True, exist_ok=True)
    (user_dir(name) / "mein-skill.md").write_text("# Skill")
    bp.save_flow(Flow(flow_id="morgens", owner=name, name="Morgens", nodes=[], edges=[]), modified_by=name)
    sched_db.create(owner=name, scope="user", project_id=None, target_type="buddy", target_id="",
                    title="Jede Stunde", prompt="wie geht's", execution_mode="direct", interval_seconds=3600)
    user_preferences.patch(uid, {"active_vault_scope": "family"})
    discord_config.save(name, discord_config.DiscordConfig(bot_token="DiscordBotGeheim-1234567890"))
    wa_config.save(name, wa_config.WhatsAppConfig(owner_numbers=["4915112345678"]))
    from hydrahive.zahnfee import storage as zahnfee
    zahnfee.save(zahnfee.Briefing(generated_at="x", date="2026-10-13", open_items="", went_well="",
                                  went_badly="", today="Termin"), name)
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO prompt_archive (id, user_id, title, prompt, created_at, updated_at) "
                     "VALUES (?, ?, 'Bild', 'ein Haus', 'x', 'x')", (f"pa-{uid}", uid))
    return {"name": name, "uid": uid, "own": own, "foreign": foreign, "agent": agent,
            "in_foreign": in_foreign, "chat": chat, "foreign_chat": foreign_chat}


def _leftovers(name: str, uid: str) -> list[str]:
    """Alles, was nach dem Löschen noch am Namen oder an der ID hängt."""
    from hydrahive.agents import config as agent_config
    from hydrahive.api.middleware import api_keys
    from hydrahive.butler import persistence as bp
    from hydrahive.communication.discord.config import _config_file as discord_file
    from hydrahive.communication.whatsapp.config import _config_file as wa_file
    from hydrahive.zahnfee.storage import _path as zahnfee_file
    from hydrahive.credentials.store import _file_for
    from hydrahive.db.connection import db
    from hydrahive.projects import _config_io, _members_model
    from hydrahive.schedules import db as sched_db
    from hydrahive.skills._paths import user_dir
    out = []
    out += [f"agent {a['id']}" for a in agent_config.list_by_owner(name)]
    out += [f"projekt {p['id']}" for p in _config_io.list_all() if _members_model.is_member(p, name)]
    out += ["credentials"] if _file_for(name).exists() else []
    out += ["skills"] if user_dir(name).exists() else []
    out += [f"butler {f.flow_id}" for f in bp.list_flows(owner=name)]
    out += [f"zeitplan {t.task_id}" for t in sched_db.list_(owner=name)]
    out += ["keys"] if api_keys.list_keys(username=name) else []
    with db() as conn:
        prefs = conn.execute("SELECT 1 FROM user_preferences WHERE user_id = ?", (uid,)).fetchone()
    out += ["prefs"] if prefs else []
    out += ["discord"] if discord_file(name).exists() else []
    out += ["whatsapp"] if wa_file(name).exists() else []
    out += ["zahnfee"] if zahnfee_file(name).exists() else []
    with db() as conn:
        out += ["prompt_archive"] if conn.execute("SELECT 1 FROM prompt_archive WHERE user_id = ?",
                                                  (uid,)).fetchone() else []
        out += ["sessions"] if conn.execute("SELECT 1 FROM sessions WHERE user_id = ?", (name,)).fetchone() else []
    return out


@pytest.mark.parametrize("mode", ["archive", "permanent"])
def test_nothing_hangs_on_the_name_afterwards(archive_root, victim, mode) -> None:
    from hydrahive.agents import config as agent_config
    from hydrahive.api.middleware import users
    from hydrahive.projects import config as project_config

    result = deletion.run("user", victim["name"], mode, actor="admin")

    assert result["state"] == "done", result
    assert users.get_by_username(victim["name"]) is None
    assert _leftovers(victim["name"], victim["uid"]) == []
    assert not session_exists(victim["chat"])
    assert project_config.get(victim["own"]["id"]) is None
    foreign = project_config.get(victim["foreign"]["id"])
    assert foreign is not None
    moved = agent_config.get(victim["in_foreign"]["id"])
    assert moved is not None and moved["owner"] == "testuser"


def test_namesake_inherits_nothing(archive_root, victim) -> None:
    """Fehler 2: Ein neuer Nutzer mit gleichem Namen sieht nichts vom alten."""
    from hydrahive.api.middleware import users
    deletion.run("user", victim["name"], "permanent", actor="admin")

    new_uid = users.create(victim["name"], "anderespasswort1", role="user")

    assert _leftovers(victim["name"], new_uid) == []


def test_user_package_and_own_project_package(archive_root, victim) -> None:
    deletion.run("user", victim["name"], "archive", actor="admin")

    [user_tgz] = packages(archive_root, "users")
    content = names(user_tgz)
    assert "user/user.json" in content
    user = json.loads(read_member(user_tgz, "user/user.json"))
    assert user["username"] == victim["name"] and "password_hash" not in user
    assert f"agents/{victim['agent']['id']}/agent/config.json" in content
    assert f"sessions/{victim['chat']}.json" in content
    assert f"sessions/{victim['foreign_chat']}.json" in content
    assert "credentials.json" in content and "skills/mein-skill.md" in content
    assert "butler/morgens.json" in content and "db/scheduled_agent_tasks.jsonl" in content
    assert "db/user_preferences.jsonl" in content and "db/prompt_archive.jsonl" in content
    assert "whatsapp.json" in content and "zahnfee.json" in content
    assert "nas-geheim-passwort" not in read_member(user_tgz, "credentials.json")
    discord = read_member(user_tgz, "discord.json")
    assert "DiscordBotGeheim" not in discord and json.loads(discord)["bot_token"] == "***"
    assert f"agents/{victim['in_foreign']['id']}/agent/config.json" not in content
    [proj_tgz] = packages(archive_root, "projects")
    assert meta(proj_tgz)["extra"]["part_of"] == meta(user_tgz)["file"]
    assert meta(proj_tgz)["source_id"] == victim["own"]["id"]


def test_scheduled_buddy_does_not_come_back(archive_root, victim) -> None:
    """Vorher: Ein Butler-/Intervall-Lauf hätte dem Gelöschten einen neuen Buddy angelegt."""
    import asyncio

    from hydrahive.agents import config as agent_config
    from hydrahive.schedules import db as sched_db
    from hydrahive.schedules.execution import _run_direct_task
    [task] = sched_db.list_(owner=victim["name"])
    deletion.run("user", victim["name"], "permanent", actor="admin")

    asyncio.run(_run_direct_task(task, "lauf-1"))

    assert agent_config.list_by_owner(victim["name"]) == []


def test_failed_package_keeps_user(archive_root, victim, monkeypatch) -> None:
    from hydrahive.api.middleware import users
    from hydrahive.archive import package

    def boom(**kw):
        raise OSError("Platte voll")

    monkeypatch.setattr(package, "pack", boom)
    result = deletion.run("user", victim["name"], "archive", actor="admin")

    assert result["state"] == "failed"
    assert users.get_by_username(victim["name"]) is not None and session_exists(victim["chat"])
    assert packages(archive_root, "users") == [] and packages(archive_root, "projects") == []


def test_preview_lists_what_stays(archive_root, victim) -> None:
    from hydrahive.vms import db as vms_db
    vms_db.create_vm(owner=victim["name"], name=f"{victim['name']}-vm", cpu=1, ram_mb=512, disk_gb=1,
                     qcow2_path="/nirgends/opfer.qcow2")

    p = deletion.preview("user", victim["name"])

    assert p["name"] == victim["name"] and p["projects"] == [{"id": victim["own"]["id"], "name": "Eigenes Projekt"}]
    assert p["stays"]["vms"] == 1
    assert p["archive"]["possible"] is True
