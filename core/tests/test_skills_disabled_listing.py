from __future__ import annotations


def test_agent_skill_listing_can_include_disabled_skills(client, auth_headers, monkeypatch):
    from hydrahive.agents import config as agent_config
    from hydrahive.api.routes import skills as skills_route
    from hydrahive.buddy import get_or_create_buddy
    from hydrahive.skills.models import Skill

    state = get_or_create_buddy("testuser")
    agent_config.update(state["agent_id"], disabled_skills=["debugging"])
    captured: list[list[str]] = []

    def fake_list(agent_id, owner, *, disabled, project_id=None):
        captured.append(disabled)
        if disabled:
            return []
        return [
            Skill(
                name="debugging",
                description="Find bugs",
                when_to_use="when broken",
                body="body",
                scope="system",
                owner="system",
            )
        ]

    monkeypatch.setattr(skills_route, "list_for_agent", fake_list)

    filtered = client.get(f"/api/skills?agent_id={state['agent_id']}", headers=auth_headers)
    complete = client.get(
        f"/api/skills?agent_id={state['agent_id']}&include_disabled=true",
        headers=auth_headers,
    )

    assert filtered.status_code == 200
    assert filtered.json() == []
    assert complete.status_code == 200
    assert [skill["name"] for skill in complete.json()] == ["debugging"]
    assert captured == [["debugging"], []]
