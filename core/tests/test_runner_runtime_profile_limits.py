from hydrahive.agentlink.runtime_profiles import RUNTIME_METADATA_KEY
from hydrahive.runner.runner import _runtime_limits


def test_runner_uses_session_profile_limits_for_agentlink_session():
    agent = {"max_iterations": 80, "max_tokens": 48_000}
    metadata = {
        RUNTIME_METADATA_KEY: {
            "version": 1,
            "profile": "standard",
            "max_iterations": 999,
            "max_tokens": 999_999,
            "timeout_seconds": 9_999,
        }
    }

    assert _runtime_limits(agent, metadata) == (32, 16_384)


def test_runner_keeps_agent_caps_for_ordinary_chat_session():
    agent = {"max_iterations": 80, "max_tokens": 48_000}

    assert _runtime_limits(agent, {}) == (80, 48_000)
