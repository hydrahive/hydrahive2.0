"""Till 28.11.: Läufe ohne Nutzer vor dem Bildschirm (Auftrag, Hintergrund, Zustellung) arbeiten durch statt zu fragen.

Kleinkram (Farbe, Name, Reihenfolge, Lösungsweg) entscheidet der Agent selbst und schreibt es in den Bericht. Stehen bleiben
nur bei echten Hindernissen. Im direkten Chat bleibt die kurze Rückfrage erlaubt.
"""
from __future__ import annotations

from hydrahive.runner._autonomy_rule import AUTONOMY_RULE, with_autonomy_rule


def test_regel_haengt_nur_an_unbeaufsichtigten_laeufen():
    for origin in ("delegation", "handoff"):
        assert AUTONOMY_RULE in with_autonomy_rule("BASIS", origin)
    for origin in ("chat", "other", None):
        assert with_autonomy_rule("BASIS", origin) == "BASIS"


def test_regel_nennt_die_echten_hindernisse_und_den_bericht():
    for stichwort in ("Zugang", "unumkehrbar", "Prod", "Kosten", "Sicherheit", "Bericht", "selbst"):
        assert stichwort in AUTONOMY_RULE, stichwort


def test_zustelltext_verlangt_keine_rueckfrage_mehr():
    from hydrahive.runner._delegation_message import FOOTER
    assert "nur nach Rückfrage" not in FOOTER
    assert "zu Ende" in FOOTER


def test_runner_haengt_regel_an_zustelllauf_nicht_an_chat(monkeypatch):
    """Im echten Runner: Zustell-Lauf bekommt den Block im stabilen Prompt, Chat nicht (LLM-Aufruf aufgezeichnet)."""
    import asyncio
    from hydrahive.agents import config as agent_config
    from hydrahive.db import init_db
    from hydrahive.db import sessions as sessions_db
    from hydrahive.runner import _run_origin
    from hydrahive.runner import runner as runner_mod
    from hydrahive.runner._runner_iter import IterationResult

    seen: list[str] = []

    async def fake_stream(**kwargs):
        seen.append(kwargs["stable_system"])
        yield IterationResult(blocks=[{"type": "text", "text": "ok"}], stop_reason="end_turn",
                              used_model=kwargs["primary_model"], input_tokens=1, output_tokens=1,
                              cache_creation_tokens=0, cache_read_tokens=0)

    monkeypatch.setattr(runner_mod, "stream_llm_call", fake_stream)
    init_db()
    a = agent_config.create(agent_type="master", name="autonomie-probe", llm_model="claude-3-7-sonnet-20250219",
                            owner="admin", tools=[], temperature=0.5, max_tokens=1000, thinking_budget=0)
    try:
        for origin in (_run_origin.CHAT, _run_origin.delegation(1)):
            s = sessions_db.create(agent_id=a["id"], user_id="admin", title="autonomie")

            async def drain(sid=s.id, o=origin):
                async for _ in runner_mod.run(sid, "hallo", origin=o):
                    pass
            asyncio.run(drain())
        assert AUTONOMY_RULE not in seen[0] and AUTONOMY_RULE in seen[1]
    finally:
        agent_config.delete(a["id"])
