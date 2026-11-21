"""ask_agent lehnt unbekannte Ziele ohne „@“ sofort ab (Idee 935d541b, 21.11.2026).

Befund: Ein Tippfehler im Agent-Namen fiel still auf ``TargetResolution()``
zurück und wurde als externes AgentLink-Ziel verschickt. Am lokalen AgentLink
hört nur ``agent:hydrahive`` zu, der Aufruf hing also bis zum Timeout (600 s).
Fehlgriffe in AgentLink: „hydrahive2“, UUID eines gelöschten Agenten,
„security-auditor“, „user“.

Grundsatz (Till): Externe Ziele gibt es nur als ``name@server`` (Föderation).
Ein Ziel ohne „@“, das kein erlaubter interner Agent ist, wird abgelehnt:
sofort, ohne ``post_state``, mit Vorschlägen nur aus erlaubten Agenten.
"""
from __future__ import annotations

import uuid

import pytest

from tests.test_ask_agent_target_access import _run, made, posted  # noqa: F401  (Fixtures)


def _owner() -> str:
    return "testuser"


# Echte Fehlgriffe aus AgentLink. „user“ fehlt hier bewusst: Das ist ein eindeutiger
# Teilstring des eigenen Test-Agenten „Test Agent (testuser)“ und wird korrekt aufgelöst.
# Feste UUID (wie die des gelöschten Agenten 30d464d2…): zufällige Werte in parametrize
# ergeben unter pytest-xdist je Worker andere Test-IDs („Different tests were collected“).
@pytest.mark.parametrize(
    "target", ["hydrahive2", "security-auditor", "nutzer", "30d464d2-b440-46d4-926e-3fde95210790"],
)
def test_unknown_target_fails_without_post_state(made, posted, tmp_path, target):  # noqa: F811
    made(f"spec-{uuid.uuid4().hex[:6]}", _owner())
    res = _run(target, _owner(), tmp_path)
    assert not res.success
    assert f"Agent '{target}' unbekannt" in res.error
    assert "name@server" in res.error
    assert posted == []


def test_suggestions_come_from_own_agents(made, posted, tmp_path):  # noqa: F811
    tag = uuid.uuid4().hex[:6]
    made(f"reviewer-{tag}", _owner())
    res = _run(f"reveiwer-{tag}", _owner(), tmp_path)
    assert not res.success
    assert f"reviewer-{tag}" in res.error
    assert "Meintest du" in res.error
    assert posted == []


def test_suggestions_never_show_foreign_agents(made, posted, tmp_path):  # noqa: F811
    tag = uuid.uuid4().hex[:6]
    made(f"geheim-analyst-{tag}", "admin")
    made(f"eigener-helfer-{tag}", _owner())
    res = _run(f"geheim-analyts-{tag}", _owner(), tmp_path)
    assert not res.success
    assert f"geheim-analyst-{tag}" not in res.error
    assert posted == []


def test_no_suggestion_line_when_nothing_similar(made, posted, tmp_path):  # noqa: F811
    made(f"aaa-{uuid.uuid4().hex[:6]}", _owner())
    res = _run("zzzzzzzzzzzzzz", _owner(), tmp_path)
    assert not res.success
    assert "Meintest du" not in res.error
    assert posted == []
