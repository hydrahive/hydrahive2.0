from __future__ import annotations

from hydrahive.buddy import _config as buddy_config
from hydrahive.runner.events import Done


def test_normalize_cockpit_prefs_merges_defaults_and_drops_unknown_slots():
    prefs = buddy_config.normalize_cockpit_prefs({
        "version": 99,
        "slots": {
            "music": {"visible": False},
            "unknown": {"visible": True, "collapsed": False},
        },
        "rightRailCollapsed": True,
        "decorVariant": "aurora",
    })

    assert prefs["version"] == 1
    assert prefs["slots"]["music"] == {"visible": False, "collapsed": True}
    assert prefs["slots"]["extensions"] == {"visible": True, "collapsed": True}
    assert "unknown" not in prefs["slots"]
    assert prefs["rightRailCollapsed"] is True
    assert prefs["decorVariant"] == "aurora"


def test_normalize_cockpit_prefs_sanitizes_invalid_values():
    prefs = buddy_config.normalize_cockpit_prefs({
        "slots": {"moduleWidgets": {"visible": "yes", "collapsed": None}},
        "rightRailCollapsed": "no",
        "decorVariant": "neon",
    })

    assert prefs["slots"]["moduleWidgets"] == {"visible": True, "collapsed": False}
    assert prefs["rightRailCollapsed"] is False
    assert prefs["decorVariant"] == "default"


def test_get_and_put_cockpit_prefs_use_buddy_memory(monkeypatch):
    store = {}
    monkeypatch.setattr(buddy_config, "_find_buddy", lambda username: {"id": f"buddy-{username}"})
    monkeypatch.setattr(buddy_config.memory, "read_key", lambda aid, key: store.get((aid, key)))
    monkeypatch.setattr(buddy_config.memory, "write_key", lambda aid, key, value: store.__setitem__((aid, key), value))

    assert buddy_config.get_cockpit_prefs("till") == buddy_config.DEFAULT_COCKPIT_PREFS

    saved = buddy_config.put_cockpit_prefs("till", {
        "slots": {"futureBottom": {"visible": True, "collapsed": False}},
        "decorVariant": "calm",
    })

    assert saved["slots"]["futureBottom"] == {"visible": True, "collapsed": False}
    assert saved["decorVariant"] == "calm"
    assert store[("buddy-till", "_pref_cockpit")] == saved


def test_done_event_carries_model_and_provider_defaults():
    done = Done(message_id="m1", iterations=1, model="claude-sonnet", provider="anthropic")

    assert done.model == "claude-sonnet"
    assert done.provider == "anthropic"
