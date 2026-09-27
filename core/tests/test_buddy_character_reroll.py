"""/character würfelt eine neue Figur, ohne Einstellungen zu verlieren.

Regression: reroll_character baute den Soul nur mit Name und Figur neu (Sprache,
Ton und Kontext fielen auf Standard zurück) und legte die neue Session ohne
Projekt an. Außerdem wurden Figurennamen mit Klammern beim späteren Neuaufbau
abgeschnitten, z. B. „Marlin (Findet Nemo)“.
"""
from __future__ import annotations

import pytest

USER = "reroll-user"


@pytest.fixture(scope="module", autouse=True)
def _init_db(setup_test_env):
    from hydrahive.db import init_db

    init_db()


@pytest.fixture(autouse=True)
def _clean(setup_test_env, _init_db):
    from hydrahive.agents import config as agent_config

    def wipe():
        for a in agent_config.list_by_owner(USER):
            agent_config.delete(a["id"])

    wipe()
    yield
    wipe()


def _buddy_with_prefs():
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.buddy._config import patch_config

    get_or_create_buddy(USER)
    patch_config(USER, {"language": "en", "tone": "knapp", "context": "Mag Katzen und Tee."})
    return get_or_create_buddy(USER)


def test_reroll_behaelt_sprache_ton_und_kontext():
    from hydrahive.agents import config as agent_config
    from hydrahive.buddy.commands import reroll_character

    state = _buddy_with_prefs()
    reroll_character(USER)
    soul = agent_config.get_system_prompt(state["agent_id"])
    assert "You always respond in English" in soul
    assert "extrem kurz" in soul
    assert "Mag Katzen und Tee." in soul


def test_reroll_behaelt_die_projektbindung(monkeypatch):
    from hydrahive.buddy import commands, get_or_create_buddy
    from hydrahive.db import sessions as sessions_db

    state = get_or_create_buddy(USER)
    sessions_db.set_project(state["session_id"], "projekt-x")
    result = commands.reroll_character(USER)
    assert sessions_db.get(result["session_id"]).project_id == "projekt-x"


def test_figur_mit_klammern_bleibt_beim_neuaufbau_erhalten(monkeypatch):
    from hydrahive.agents import config as agent_config
    from hydrahive.buddy import _config, commands

    monkeypatch.setattr(commands, "_pick_character", lambda: ("Pixar", "Marlin (Findet Nemo)"))
    state = _buddy_with_prefs()
    commands.reroll_character(USER)
    _config.patch_config(USER, {"tone": "locker"})
    soul = agent_config.get_system_prompt(state["agent_id"])
    assert "**Marlin (Findet Nemo)** aus **Pixar**" in soul
