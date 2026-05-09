"""Tests für Memory v2 Store-Logic — pure Functions ohne File-IO.

Deckt: _migrate_entry, _is_expired, _parse_expiry, _reinforce_confidence,
_jaccard_similarity, _project_matches, find_contradictions, mark_superseded.

Keine LLM-Calls. Compress/Crystallize-Pipelines (_compress.py, _crystallize.py)
sind reine LLM-Wrapper und bekommen Smoke-Tests separat.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hydrahive.tools._memory_store import (
    _is_expired,
    _jaccard_similarity,
    _migrate_entry,
    _parse_expiry,
    _project_matches,
    _reinforce_confidence,
    find_contradictions,
    is_expired,
    mark_superseded,
)


# --- _migrate_entry ------------------------------------------------------

def test_migrate_string_zu_full_entry():
    entry = _migrate_entry("plain string content")
    assert entry["content"] == "plain string content"
    assert entry["confidence"] == 0.5
    assert entry["is_latest"] is True
    assert entry["supersedes"] == []
    assert entry["project"] is None


def test_migrate_alter_dict_setzt_defaults():
    """Bestehende Felder bleiben, fehlende bekommen Defaults."""
    entry = _migrate_entry({"content": "x", "created_at": "2026-01-01T00:00:00Z"})
    assert entry["content"] == "x"
    assert entry["created_at"] == "2026-01-01T00:00:00Z"
    assert entry["confidence"] == 0.5
    assert entry["reinforcements"] == 0
    assert entry["is_latest"] is True


def test_migrate_dict_mit_eigenen_werten_nicht_ueberschrieben():
    entry = _migrate_entry({"content": "x", "confidence": 0.9, "is_latest": False})
    assert entry["confidence"] == 0.9
    assert entry["is_latest"] is False


# --- _is_expired ---------------------------------------------------------

def test_is_expired_kein_expires_at_false():
    assert _is_expired({"content": "x"}) is False
    assert _is_expired({"expires_at": None}) is False


def test_is_expired_zukunft_false():
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert _is_expired({"expires_at": future}) is False


def test_is_expired_vergangenheit_true():
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert _is_expired({"expires_at": past}) is True


def test_is_expired_ungueltiger_string_false():
    """Defensive: kaputtes Datum → nicht abgelaufen (nicht crashen)."""
    assert _is_expired({"expires_at": "not-a-date"}) is False


def test_is_expired_public_alias():
    assert is_expired({"content": "x"}) is False


# --- _parse_expiry -------------------------------------------------------

def test_parse_expiry_relative_stunden():
    result = _parse_expiry("+2h")
    parsed = datetime.fromisoformat(result)
    expected = datetime.now(timezone.utc) + timedelta(hours=2)
    diff = abs((parsed - expected).total_seconds())
    assert diff < 5  # < 5s Toleranz


def test_parse_expiry_relative_tage():
    result = _parse_expiry("+7d")
    parsed = datetime.fromisoformat(result)
    expected = datetime.now(timezone.utc) + timedelta(days=7)
    assert abs((parsed - expected).total_seconds()) < 5


def test_parse_expiry_relative_wochen():
    result = _parse_expiry("+4w")
    parsed = datetime.fromisoformat(result)
    expected = datetime.now(timezone.utc) + timedelta(weeks=4)
    assert abs((parsed - expected).total_seconds()) < 5


def test_parse_expiry_relative_monate_30d_pro_monat():
    result = _parse_expiry("+2m")
    parsed = datetime.fromisoformat(result)
    expected = datetime.now(timezone.utc) + timedelta(days=60)
    assert abs((parsed - expected).total_seconds()) < 5


def test_parse_expiry_absolute_iso_durchgereicht():
    iso = "2030-01-01T00:00:00+00:00"
    assert _parse_expiry(iso) == iso


def test_parse_expiry_kaputtes_format_durchgereicht():
    """Was nicht matched, wird unverändert zurückgegeben (Caller entscheidet)."""
    assert _parse_expiry("garbage") == "garbage"


# --- _reinforce_confidence -----------------------------------------------

def test_reinforce_steigt_konvergent():
    """new = old + 0.1 * (1 - old) → 0.5 → 0.55 → 0.595 → ..."""
    assert _reinforce_confidence(0.5) == 0.55
    assert _reinforce_confidence(0.9) == 0.91


def test_reinforce_capped_bei_1():
    assert _reinforce_confidence(0.99) <= 1.0
    assert _reinforce_confidence(1.0) == 1.0


def test_reinforce_aus_0_steigt_um_step():
    assert _reinforce_confidence(0.0) == 0.1


# --- _jaccard_similarity -------------------------------------------------

def test_jaccard_identisch_1():
    assert _jaccard_similarity("foo bar baz", "foo bar baz") == 1.0


def test_jaccard_disjunkt_0():
    assert _jaccard_similarity("aaa bbb ccc", "xxx yyy zzz") == 0.0


def test_jaccard_zwei_gemeinsame_drei_gesamt():
    """{foo, bar, baz} ∩ {foo, bar, qux} = 2, Union = 4 → 0.5"""
    sim = _jaccard_similarity("foo bar baz", "foo bar qux")
    assert sim == 0.5


def test_jaccard_kurze_woerter_gefiltert():
    """Tokens len <= 2 werden ausgefiltert (a, in, an, etc.)."""
    sim = _jaccard_similarity("foo a in", "foo a in")
    assert sim == 1.0  # "foo" matches sich selbst (a, in werden gefiltert)


def test_jaccard_einer_leer_gibt_0():
    assert _jaccard_similarity("foo bar", "") == 0.0


# --- find_contradictions -------------------------------------------------

def test_find_contradictions_ueber_threshold():
    data = {
        "alt": _migrate_entry({"content": "kommunikation slack daily standup"}),
    }
    matches = find_contradictions(data, "neu", "kommunikation slack daily standup")
    assert "alt" in matches


def test_find_contradictions_unter_threshold():
    data = {
        "alt": _migrate_entry({"content": "ganz andere domäne python build"}),
    }
    matches = find_contradictions(data, "neu", "kommunikation slack daily standup")
    assert matches == []


def test_find_contradictions_ignoriert_self():
    data = {
        "self": _migrate_entry({"content": "test content match"}),
    }
    assert "self" not in find_contradictions(data, "self", "test content match")


def test_find_contradictions_ignoriert_superseded():
    """Veraltete (is_latest=False) tauchen nie in Contradictions auf."""
    old_entry = _migrate_entry({"content": "test content match"})
    old_entry["is_latest"] = False
    data = {"alt": old_entry}
    assert find_contradictions(data, "neu", "test content match") == []


def test_find_contradictions_ignoriert_expired():
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    expired_entry = _migrate_entry({"content": "test content match", "expires_at": past})
    data = {"alt": expired_entry}
    assert find_contradictions(data, "neu", "test content match") == []


# --- mark_superseded -----------------------------------------------------

def test_mark_superseded_setzt_is_latest_false():
    data = {"old1": _migrate_entry({"content": "x"}), "old2": _migrate_entry({"content": "y"})}
    mark_superseded(data, ["old1", "old2"], by_key="new")
    assert data["old1"]["is_latest"] is False
    assert data["old2"]["is_latest"] is False
    assert data["old1"]["superseded_by"] == "new"
    assert data["old1"]["superseded_at"] is not None


def test_mark_superseded_unbekannte_keys_werden_ignoriert():
    """Robust: keys die nicht existieren werfen keinen KeyError."""
    data = {"x": _migrate_entry({"content": "y"})}
    mark_superseded(data, ["does-not-exist"], by_key="new")  # darf nicht crashen
    assert "does-not-exist" not in data


# --- _project_matches ----------------------------------------------------

def test_project_filter_star_matched_alles():
    entry = _migrate_entry({"content": "x", "project": "alpha"})
    assert _project_matches(entry, "*", None) is True


def test_project_filter_explicit_zeigt_eigene_und_globale():
    proj_entry = _migrate_entry({"content": "x", "project": "alpha"})
    global_entry = _migrate_entry({"content": "y", "project": None})
    other_entry = _migrate_entry({"content": "z", "project": "beta"})
    assert _project_matches(proj_entry, "alpha", None) is True
    assert _project_matches(global_entry, "alpha", None) is True
    assert _project_matches(other_entry, "alpha", None) is False


def test_project_kein_kontext_zeigt_nur_globale():
    proj_entry = _migrate_entry({"content": "x", "project": "alpha"})
    global_entry = _migrate_entry({"content": "y", "project": None})
    assert _project_matches(proj_entry, None, None) is False
    assert _project_matches(global_entry, None, None) is True
