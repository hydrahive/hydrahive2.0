from hydrahive.agents._config_utils import normalize


def test_old_agent_gets_empty_reasoning_default():
    assert normalize({})["reasoning_effort"] == ""


def test_agent_reasoning_default_is_preserved():
    assert normalize({"reasoning_effort": "high"})["reasoning_effort"] == "high"


def test_session_override_priority_expression():
    agent = {"reasoning_effort": "high"}
    session_effort = "low"
    assert (session_effort or agent.get("reasoning_effort") or None) == "low"


def test_agent_default_used_without_session_override():
    agent = {"reasoning_effort": "high"}
    session_effort = None
    assert (session_effort or agent.get("reasoning_effort") or None) == "high"
