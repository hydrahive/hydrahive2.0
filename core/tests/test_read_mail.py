"""read_mail-Tool: aktives Lesen des Postfachs (Gegenstück zu send_mail).

Teilt die Single-Source-IMAP-Config (settings.mail_imap_* + optionaler per-Agent
`imap`-Override) und die Fetch-Logik des Watchers. Read-only, stört den Watcher
nicht. Lazy imports + gefälschtes IMAP, kein echtes Netz.
"""
from __future__ import annotations

import asyncio
from email.message import EmailMessage
from pathlib import Path


def _ctx(config=None):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s", agent_id="a", user_id="u",
                       workspace=Path("/tmp"), config=config or {})


def _raw(from_="Alex <alex@example.com>", subject="Hallo", body="Hallo Bot",
         msg_id="<m1@example.com>") -> bytes:
    m = EmailMessage()
    m["From"] = from_
    m["To"] = "bot@hive.de"
    m["Subject"] = subject
    m["Message-ID"] = msg_id
    m["Date"] = "Mon, 01 Jun 2026 10:00:00 +0000"
    m.set_content(body)
    return m.as_bytes()


class _FakeIMAP:
    def __init__(self, raws):
        self._raws = raws

    def login(self, user, password):
        pass

    def select(self, folder, readonly=False):
        assert readonly is True          # read_mail darf nichts verändern
        return ("OK", [b"1"])

    def search(self, charset, *criteria):
        ids = " ".join(str(i + 1) for i in range(len(self._raws)))
        return ("OK", [ids.encode()])

    def fetch(self, mid, parts):
        return ("OK", [(b"x", self._raws[int(mid) - 1])])

    def logout(self):
        pass


def _patch_imap(monkeypatch, raws):
    from hydrahive.communication.mail import imap_poll
    monkeypatch.setattr(imap_poll.imaplib, "IMAP4_SSL", lambda host, port: _FakeIMAP(raws))


def _settings(monkeypatch, **over):
    from hydrahive.tools import read_mail
    cfg = {"imap_host": "w0.kasserver.com", "imap_port": 993,
           "imap_user": "m07", "imap_password": "pw"}
    cfg.update(over)
    monkeypatch.setattr(read_mail, "_settings_imap", lambda: cfg)


def test_unconfigured_returns_hint(monkeypatch):
    from hydrahive.tools import read_mail
    _settings(monkeypatch, imap_host="")
    res = asyncio.run(read_mail._execute({}, _ctx()))
    assert not res.success
    assert "konfiguriert" in res.error.lower() or "imap" in res.error.lower()


def test_lists_messages(monkeypatch):
    from hydrahive.tools import read_mail
    _settings(monkeypatch)
    _patch_imap(monkeypatch, [
        _raw(from_="Alex <alex@example.com>", subject="Frage A", msg_id="<a@x>"),
        _raw(from_="Bea <bea@example.com>", subject="Frage B", msg_id="<b@x>"),
    ])
    res = asyncio.run(read_mail._execute({"unread_only": False}, _ctx()))
    assert res.success
    assert "alex@example.com" in res.output and "Frage A" in res.output
    assert "bea@example.com" in res.output and "Frage B" in res.output


def test_limit_respected(monkeypatch):
    from hydrahive.tools import read_mail
    _settings(monkeypatch)
    _patch_imap(monkeypatch, [_raw(msg_id=f"<{i}@x>", subject=f"S{i}") for i in range(5)])
    res = asyncio.run(read_mail._execute({"unread_only": False, "limit": 2}, _ctx()))
    assert res.success
    assert res.metadata.get("count") == 2


def test_empty_inbox_message(monkeypatch):
    from hydrahive.tools import read_mail
    _settings(monkeypatch)
    _patch_imap(monkeypatch, [])
    res = asyncio.run(read_mail._execute({"unread_only": False}, _ctx()))
    assert res.success
    assert "keine" in res.output.lower()


def test_per_agent_imap_override_wins(monkeypatch):
    from hydrahive.tools import read_mail
    _settings(monkeypatch, imap_host="settings.host")
    cfg = read_mail._resolve_imap_cfg(
        {"imap": {"host": "agent.host", "user": "u2", "password": "p2", "port": 993}})
    assert cfg["imap_host"] == "agent.host"
    assert cfg["imap_user"] == "u2"
