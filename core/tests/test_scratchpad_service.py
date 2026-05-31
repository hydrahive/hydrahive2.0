from __future__ import annotations

import pytest

from hydrahive.scratchpad import service
from hydrahive.scratchpad.service import ScratchpadTooLarge


@pytest.fixture
def sp(tmp_path, monkeypatch):
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    return service


def test_get_user_empty_when_absent(sp):
    assert sp.get_user("u1") == ""


def test_save_and_get_user(sp):
    sp.save_user("u1", "meine idee")
    assert sp.get_user("u1") == "meine idee"


def test_zones_are_independent(sp):
    sp.save_user("u1", "USER-TEXT")
    sp.save_agent("u1", "AGENT-TEXT")
    assert sp.get_user("u1") == "USER-TEXT"
    assert sp.get_agent("u1") == "AGENT-TEXT"


def test_save_agent_never_touches_user_zone(sp):
    """Kern-Garantie: der Agent kann Tills Text technisch nicht überschreiben."""
    sp.save_user("u1", "TILLS UNANTASTBARER TEXT")
    sp.save_agent("u1", "agent kritzelt")
    assert sp.get_user("u1") == "TILLS UNANTASTBARER TEXT"


def test_clear_agent_only(sp):
    sp.save_user("u1", "bleibt")
    sp.save_agent("u1", "geht weg")
    sp.clear_agent("u1")
    assert sp.get_agent("u1") == ""
    assert sp.get_user("u1") == "bleibt"


def test_users_isolated(sp):
    sp.save_user("u1", "A")
    sp.save_user("u2", "B")
    assert sp.get_user("u1") == "A"
    assert sp.get_user("u2") == "B"


def test_combined_contains_both_zones(sp):
    sp.save_user("u1", "IDEE-X")
    sp.save_agent("u1", "NOTIZ-Y")
    combined = sp.get_combined("u1")
    assert "IDEE-X" in combined
    assert "NOTIZ-Y" in combined


def test_too_large_rejected(sp):
    with pytest.raises(ScratchpadTooLarge):
        sp.save_user("u1", "x" * (256 * 1024 + 1))
