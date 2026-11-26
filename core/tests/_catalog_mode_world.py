"""Gemeinsamer Aufbau für die Katalog-Modus-Tests (Plan Aufgabe 5): echter Runner, LLM-Aufruf durch Aufzeichnung ersetzt."""
from __future__ import annotations

import asyncio

from hydrahive.agents import config as agent_config
from hydrahive.db import init_db
from hydrahive.db import sessions as sessions_db
from hydrahive.runner import runner as runner_mod
from hydrahive.runner._runner_iter import IterationResult
from hydrahive.skills.models import Skill

MODEL = "claude-3-7-sonnet-20250219"
FESTE_SKILLS = [
    Skill(name="debugging", description="Fehler suchen", when_to_use="wenn etwas nicht funktioniert", body="b",
          scope="system", owner="system"),
    Skill(name="docs", description="Doku schreiben", when_to_use="wenn Doku gebraucht wird", body="b",
          scope="system", owner="system"),
]
CLASSIC_TOOLS = ["shell_exec", "file_read", "file_write", "web_search", "send_mail", "todo_write", "load_skill"]


def snapshot(call: dict) -> dict:
    """Was beim Modell ankommt, ohne Laufzeit-Zufälle (Arbeitsordner, Agent-ID/-Name im Prompt)."""
    import re
    stable = re.sub(r"Workspace: .*", "Workspace: <WS>", call["stable"])
    return {"tools": [t["name"] for t in call["tools"]], "schemas": call["tools"], "stable": stable}


class World:
    def __init__(self, client, monkeypatch):
        self.calls: list[dict] = []
        self.script: list[list[dict]] = []          # je LLM-Aufruf die Antwortblöcke (Standard: nur Text)
        self.made: list[str] = []
        self.monkeypatch = monkeypatch
        init_db()

        async def fake_stream(**kwargs):
            self.calls.append({"stable": kwargs["stable_system"], "volatile": kwargs["volatile_system"],
                               "tools": kwargs["tool_schemas"]})
            n = len(self.calls) - 1
            blocks = self.script[n] if n < len(self.script) else [{"type": "text", "text": "ok"}]
            stop = "tool_use" if any(b.get("type") == "tool_use" for b in blocks) else "end_turn"
            yield IterationResult(blocks=blocks, stop_reason=stop, used_model=kwargs["primary_model"],
                                  input_tokens=1, output_tokens=1, cache_creation_tokens=0, cache_read_tokens=0)

        monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
        monkeypatch.setattr(runner_mod, "load_agent_skills", lambda *a, **k: list(FESTE_SKILLS))

    def agent(self, *, tools=None, owner="admin", **extra) -> str:
        a = agent_config.create(agent_type="master", name=f"km-{len(self.made)}", llm_model=MODEL, owner=owner,
                                created_by=owner, temperature=0.7, max_tokens=1000, thinking_budget=0,
                                tools=list(tools if tools is not None else CLASSIC_TOOLS))
        if extra:
            agent_config.update(a["id"], **extra)
        self.made.append(a["id"])
        return a["id"]

    def session(self, agent_id: str, user: str = "admin") -> str:
        return sessions_db.create(agent_id=agent_id, user_id=user, title="km").id

    def run(self, session_id: str, text: str = "hallo") -> list[dict]:
        before = len(self.calls)

        async def go():
            async for _ in runner_mod.run(session_id, text):
                pass
        asyncio.run(go())
        return self.calls[before:]

    def cleanup(self) -> None:
        for aid in self.made:
            agent_config.delete(aid)
