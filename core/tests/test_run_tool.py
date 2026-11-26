"""Katalog Etappe 2, Aufgabe 2: run_tool wird im Runner VOR allen Prüfungen ausgepackt (Spec E4, S1, K10/K11).

Aus run_tool(name, args) wird intern ein normaler Tool-Aufruf {name: inner, input: args, via: "run_tool"}, der denselben Weg
nimmt wie ein direkter: Bestätigung (Harakiri), vault_gate, tool_denied, Container-Allowlist, tool_calls, agent_tree.
run_tool selbst ist in keiner Agenten-Config freigeschaltet; die Tests setzen es nur in allowed_tools des Laufs.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from hydrahive.runner import _runner_tools, tool_confirmation
from hydrahive.runner.events import ToolConfirmRequired, ToolUseResult
from hydrahive.tools._launcher import DevLauncher, LaunchResult, set_launcher
from hydrahive.tools.base import ToolContext, ToolResult


class FakeLauncher:
    def __init__(self):
        self.calls: list[str] = []

    async def run(self, cmd, cwd, timeout=60, env=None):
        self.calls.append(cmd)
        return LaunchResult(exit_code=0, stdout="ok", stderr="")


def _ctx(ws: Path, **kw) -> ToolContext:
    return ToolContext(session_id="s1", agent_id="", user_id="u1", workspace=ws, **kw)


def _rt(inner: str, args: dict, call_id: str = "c1") -> dict:
    return {"id": call_id, "name": "run_tool", "input": {"name": inner, "args": args}}


async def _drive(tool_uses, ctx, allowed, *, require_confirm=False):
    events = []
    async for item in _runner_tools.process_tool_uses(
        tool_uses, ctx=ctx, allowed_tools=allowed, parent_message_id="m1",
        require_confirm=require_confirm, tool_result_max_chars=10000,
    ):
        events.append(item)
    return events


def _results(events) -> list[ToolUseResult]:
    return [e for e in events if isinstance(e, ToolUseResult)]


@pytest.fixture
def launcher(monkeypatch):
    fake = FakeLauncher()
    set_launcher(fake)
    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)
    tool_confirmation._pending.clear()
    yield fake
    set_launcher(DevLauncher())
    tool_confirmation._pending.clear()


@pytest.fixture
def recorded(monkeypatch):
    """Fängt execute_tool ab: welcher Name/welche Eingabe wirklich beim Dispatcher ankommt."""
    seen: list[dict] = []

    async def _fake(*, tool_use, allowed_tools, ctx, parent_message_id, iteration=None):
        seen.append({"tool_use": tool_use, "allowed": list(allowed_tools)})
        return ToolResult.ok("lief"), "rec1", 1

    monkeypatch.setattr(_runner_tools, "execute_tool", _fake)
    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)
    tool_confirmation._pending.clear()
    return seen


async def _deny(call_id, timeout=0):
    return "deny"


# --- K10: jeder Sperrgrund greift auch über run_tool ----------------------------------------------------------------

def test_shell_ueber_run_tool_loest_harakiri_aus(launcher, monkeypatch, tmp_path):
    """Äußerer Name ist run_tool – trotzdem muss die Bestätigung wie bei direktem shell_exec erscheinen."""
    monkeypatch.setattr(tool_confirmation, "wait", _deny)
    events = asyncio.run(_drive([_rt("shell_exec", {"cmd": "rm -rf /opt/searxng"})], _ctx(tmp_path),
                                ["run_tool", "shell_exec"]))
    confirms = [e for e in events if isinstance(e, ToolConfirmRequired)]
    assert len(confirms) == 1 and confirms[0].tool_name == "shell_exec"
    assert confirms[0].reason and "/opt" in confirms[0].reason
    assert launcher.calls == [], "nach Ablehnung darf nichts laufen"


def test_vault_gesperrt_auch_ueber_run_tool(monkeypatch, tmp_path, client):
    """vault_gate sieht den INNEREN Namen: bei gesperrtem Vault läuft das Vault-Werkzeug nicht."""
    from hydrahive.db import messages as messages_db
    from hydrahive.db import sessions as sessions_db
    from hydrahive.vault import agent_gate
    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)
    monkeypatch.setattr(agent_gate, "vault_tools", lambda: frozenset({"read_memory"}))
    monkeypatch.setattr("hydrahive.vault.unlocks.use", lambda uid: False, raising=False)
    monkeypatch.setattr("hydrahive.access.check.user_id_for", lambda u: "uid-1")
    monkeypatch.setattr("hydrahive.runner.dispatcher.tool_denied", lambda u, t: None)
    s = sessions_db.create(agent_id="a1", user_id="u1", title="t")
    msg = messages_db.append(s.id, "assistant", "hi")
    ctx = ToolContext(session_id=s.id, agent_id="a1", user_id="u1", workspace=tmp_path)

    async def go():
        return [e async for e in _runner_tools.process_tool_uses(
            [_rt("read_memory", {"key": "x"})], ctx=ctx, allowed_tools=["run_tool", "read_memory"],
            parent_message_id=msg.id, require_confirm=False, tool_result_max_chars=10000)]

    res = _results(asyncio.run(go()))
    assert res and res[0].success is False and "Vault" in (res[0].error or "")


def test_run_tool_auf_run_tool_abgelehnt(recorded, tmp_path):
    for inner in ("run_tool", "find_tools", "find_skills"):
        events = asyncio.run(_drive([_rt(inner, {})], _ctx(tmp_path), ["run_tool", "find_tools", "find_skills"]))
        res = _results(events)
        assert res and res[0].success is False and inner in (res[0].error or "")
    assert recorded == [], "kein Aufruf des Dispatchers"


def test_container_projekt_run_tool_ausserhalb_allowlist_abgelehnt(tmp_path):
    """Im Container-Projekt enthält die Freigabe des Laufs nur die Allowlist; run_tool(web_browser) wird abgelehnt."""
    from hydrahive.runner._project_tool_scope import scope_tools
    ct = {"id": "p", "mcp_server_ids": [], "allowed_plugins": [],
          "execution": {"mode": "container", "container": "hh-labor-probe", "workdir": "/work", "user": 1000}}
    allowed, _ = scope_tools(ct, ["file_read", "web_browser", "send_mail"], [])
    events = asyncio.run(_drive([_rt("web_browser", {"url": "http://x"})], _ctx(tmp_path), ["run_tool", *allowed]))
    res = _results(events)
    assert res and res[0].success is False and "nicht erlaubt" in (res[0].error or "")


def test_nicht_freigegebenes_tool_abgelehnt(recorded, tmp_path):
    events = asyncio.run(_drive([_rt("send_mail", {"to": "a@b.c"})], _ctx(tmp_path), ["run_tool", "file_read"]))
    res = _results(events)
    assert res and res[0].success is False and "nicht erlaubt" in (res[0].error or "")
    assert recorded == []


def test_args_passen_nicht_zum_schema(recorded, tmp_path):
    """Erfundenes Feld: klare Meldung mit den erlaubten Feldern, kein Aufruf, kein Absturz (Review-Fokus 2)."""
    events = asyncio.run(_drive([_rt("file_read", {"pfad": "x.txt"})], _ctx(tmp_path), ["run_tool", "file_read"]))
    res = _results(events)
    assert res and res[0].success is False
    err = res[0].error or ""
    assert "pfad" in err and "path" in err and "offset" in err, err      # nennt das falsche und die erlaubten Felder
    assert recorded == []
    events = asyncio.run(_drive([_rt("file_read", {})], _ctx(tmp_path), ["run_tool", "file_read"], ))
    assert "path" in (_results(events)[0].error or "") and recorded == []        # Pflichtfeld fehlt
    events = asyncio.run(_drive([_rt("file_read", {"path": 5})], _ctx(tmp_path), ["run_tool", "file_read"]))
    assert _results(events)[0].success is False and recorded == []                # falscher Typ


# --- K11: Sichtbarkeit in tool_calls / agent_tree --------------------------------------------------------------------

def test_tool_calls_zeigt_inneren_namen_und_via(monkeypatch, tmp_path, client):
    from hydrahive.db import messages as messages_db
    from hydrahive.db import sessions as sessions_db
    from hydrahive.db import tools as tools_db
    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)
    s = sessions_db.create(agent_id="a1", user_id="u1", title="t")
    msg = messages_db.append(s.id, "assistant", "hi")
    ctx = ToolContext(session_id=s.id, agent_id="a1", user_id="u1", workspace=tmp_path)
    (tmp_path / "datei.txt").write_text("hallo")

    async def go():
        return [e async for e in _runner_tools.process_tool_uses(
            [_rt("file_read", {"path": "datei.txt"}, "tu-1")], ctx=ctx, allowed_tools=["run_tool", "file_read"],
            parent_message_id=msg.id, require_confirm=False, tool_result_max_chars=10000)]

    events = asyncio.run(go())
    assert _results(events)[0].success is True
    rows = tools_db.list_for_message(msg.id)
    assert len(rows) == 1, "genau EIN Eintrag, kein Doppel-Eintrag für run_tool"
    assert rows[0].tool_name == "file_read" and rows[0].metadata.get("via") == "run_tool"


def test_run_tool_auf_direkt_vorhandenes_tool_wie_direkt(recorded, tmp_path):
    """Review-Fokus 1: run_tool("file_read") verhält sich wie ein direkter Aufruf (gleiche Eingabe am Dispatcher)."""
    asyncio.run(_drive([_rt("file_read", {"path": "a.txt"})], _ctx(tmp_path), ["run_tool", "file_read"]))
    asyncio.run(_drive([{"id": "c2", "name": "file_read", "input": {"path": "a.txt"}}], _ctx(tmp_path),
                       ["run_tool", "file_read"]))
    assert len(recorded) == 2
    via, direct = recorded[0]["tool_use"], recorded[1]["tool_use"]
    assert via["name"] == direct["name"] == "file_read" and via["input"] == direct["input"] == {"path": "a.txt"}
    assert via.get("via") == "run_tool" and "via" not in direct


def test_agent_tree_erkennt_sperre_ueber_run_tool(launcher, tmp_path, client, monkeypatch):
    """Ein über run_tool gesperrter Shell-Befehl wird als shell_exec mit Sperre im Agenten-Baum erkannt."""
    from hydrahive.db import messages as messages_db
    from hydrahive.db import sessions as sessions_db
    from hydrahive.db import tools as tools_db
    from hydrahive.runner import agent_tree
    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)
    s = sessions_db.create(agent_id="a1", user_id="u1", title="t")
    msg = messages_db.append(s.id, "assistant", "hi")
    ctx = ToolContext(session_id=s.id, agent_id="a1", user_id="u1", workspace=tmp_path)

    async def go():
        return [e async for e in _runner_tools.process_tool_uses(
            [_rt("shell_exec", {"cmd": "ssh host ls"}, "tu-9")], ctx=ctx, allowed_tools=["run_tool", "shell_exec"],
            parent_message_id=msg.id, require_confirm=False, tool_result_max_chars=10000)]

    from hydrahive.tools import _shell_guard
    monkeypatch.setattr("hydrahive.runner.dispatcher.tool_denied", lambda u, t: None)   # Nutzer hat die Freigabe
    monkeypatch.setattr(_shell_guard, "agent_type", lambda agent_id: "project")        # Schutz gilt für Projekt-Agenten
    asyncio.run(go())
    rows = tools_db.list_for_message(msg.id)
    assert len(rows) == 1 and rows[0].tool_name == "shell_exec"
    flagged = agent_tree._row(rows[0].tool_name, json.dumps(rows[0].arguments), rows[0].status, rows[0].created_at,
                              rows[0].error_message, json.dumps(rows[0].result))
    assert flagged["tool"] == "shell_exec" and flagged["risky"] is True and flagged["blocked"] is True
    assert launcher.calls == [] and _shell_guard.BLOCK_MARKER


# --- Bausteine -------------------------------------------------------------------------------------------------------

def test_check_args_bausteine():
    from hydrahive.runner._run_tool_unwrap import check_args
    schema = {"type": "object", "properties": {"path": {"type": "string"}, "n": {"type": "integer"},
                                               "mode": {"type": "string", "enum": ["a", "b"]}}, "required": ["path"]}
    assert check_args(schema, {"path": "x", "n": 3, "mode": "a"}) is None
    assert "path" in check_args(schema, {})
    assert "mode" in check_args(schema, {"path": "x", "mode": "z"})
    assert "n" in check_args(schema, {"path": "x", "n": "drei"})
    assert "foo" in check_args(schema, {"path": "x", "foo": 1})
    assert "n" in check_args(schema, {"path": "x", "n": True}), "bool ist kein integer"


def test_run_tool_ist_registriert_aber_in_keiner_default_liste():
    from hydrahive.tools import REGISTRY
    assert "run_tool" in REGISTRY
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "src" / "hydrahive"
    allowed_files = {"run_tool.py", "_run_tool_unwrap.py", "_runner_tools.py",
                     "agents.py"}                       # agents.py: Ausblende-Liste für den Editor (Review #782)
    for f in src.rglob("*.py"):
        if f.name in allowed_files:
            continue
        code = "\n".join(l for l in f.read_text().splitlines() if not l.lstrip().startswith("#"))
        assert '"run_tool"' not in code, f"run_tool in {f}"
    # Und direkt: in keiner Standard-Liste der Agenten-Typen.
    from hydrahive.agents._defaults import DEFAULT_TOOLS
    for typ, tools in DEFAULT_TOOLS.items():
        assert "run_tool" not in tools, f"run_tool in DEFAULT_TOOLS[{typ}]"


# --- Review #782 -------------------------------------------------------------------------------------------------

def test_ohne_run_tool_freigabe_wird_nicht_ausgepackt(recorded, tmp_path):
    """Fängt (Review #782, sollte): ein classic-Agent ohne run_tool bekam einen erfundenen Aufruf ausgeführt (K7)."""
    asyncio.run(_drive([_rt("file_read", {"path": "x"})], _ctx(tmp_path), ["file_read"]))
    assert recorded and recorded[0]["tool_use"]["name"] == "run_tool", "unverändert an den Dispatcher → dort abgelehnt"
    assert "via" not in recorded[0]["tool_use"]


def test_ablehnung_beim_auspacken_steht_in_tool_calls(monkeypatch, tmp_path, client):
    """Fängt (Review #782, sollte / Spec S1): ein abgelehntes run_tool(send_mail) blieb in tool_calls unsichtbar."""
    from hydrahive.db import messages as messages_db
    from hydrahive.db import sessions as sessions_db
    from hydrahive.db import tools as tools_db
    monkeypatch.setattr(_runner_tools, "record_observation", lambda **k: None)
    s = sessions_db.create(agent_id="a1", user_id="u1", title="t")
    msg = messages_db.append(s.id, "assistant", "hi")
    ctx = ToolContext(session_id=s.id, agent_id="a1", user_id="u1", workspace=tmp_path)

    async def go():
        return [e async for e in _runner_tools.process_tool_uses(
            [_rt("send_mail", {"to": "a@b.c"}, "tu-x")], ctx=ctx, allowed_tools=["run_tool", "file_read"],
            parent_message_id=msg.id, require_confirm=False, tool_result_max_chars=10000)]

    assert _results(asyncio.run(go()))[0].success is False
    rows = tools_db.list_for_message(msg.id)
    assert len(rows) == 1
    assert rows[0].tool_name == "run_tool" and rows[0].status == "error"
    assert rows[0].metadata.get("via") == "run_tool" and "nicht erlaubt" in rows[0].metadata.get("rejected", "")


def test_mcp_ueber_run_tool_klare_meldung(recorded, tmp_path):
    events = asyncio.run(_drive([_rt("mcp__srv__x", {})], _ctx(tmp_path), ["run_tool", "mcp__srv__x"]))
    res = _results(events)
    assert res[0].success is False and "MCP" in (res[0].error or "") and "direkt" in (res[0].error or "")
    assert recorded == []


def test_loop_signatur_am_inneren_namen():
    """Fängt (Review #782, Security sollte): Wechsel run_tool(x)/x umging die Loop-Bremse (Signatur am äußeren Namen)."""
    from hydrahive.runner._run_tool_unwrap import loop_signature_input, loop_signature_name
    direkt = {"id": "a", "name": "shell_exec", "input": {"cmd": "ls"}}
    umweg = _rt("shell_exec", {"cmd": "ls"}, "b")
    assert loop_signature_name(direkt) == loop_signature_name(umweg) == "shell_exec"
    assert loop_signature_input(direkt) == loop_signature_input(umweg) == {"cmd": "ls"}
    src = (Path(__file__).resolve().parents[1] / "src/hydrahive/runner/runner.py").read_text()
    assert "loop_signature_name(tu)" in src and "loop_signature_name(tool_uses[-1])" in src


def test_run_tool_nicht_im_agenten_editor(client):
    """Bis Plan-Aufgabe 5 lässt sich run_tool nicht einzeln vergeben (Review #782)."""
    from hydrahive.api.routes import agents as agents_route
    names = {t["name"] for t in agents_route.list_available_tools(("admin", "admin"))}
    assert "run_tool" not in names and "file_read" in names
