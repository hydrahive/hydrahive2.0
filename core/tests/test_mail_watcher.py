"""Mail-Watcher (Schicht 1): IMAP-Poll → handle_incoming → SMTP-Reply.

TDD für den aus HydraHive1 portierten mail_watcher. Lazy imports (sonst friert
settings.data_dir zur Collection-Zeit ein). Kein echtes IMAP/SMTP — alles gemockt.
"""
from __future__ import annotations

import asyncio
from email.message import EmailMessage


# ---------------------------------------------------------------- _seen (Dedup)

def test_seen_roundtrip(tmp_path):
    from hydrahive.communication.mail import _seen
    p = tmp_path / "seen.json"
    _seen.save_seen(p, {"<a@x>", "<b@x>"})
    assert _seen.load_seen(p) == {"<a@x>", "<b@x>"}


def test_seen_load_missing_is_empty(tmp_path):
    from hydrahive.communication.mail import _seen
    assert _seen.load_seen(tmp_path / "nope.json") == set()


# ---------------------------------------------------------------- IMAP-Polling

def _raw_mail(*, from_="Alex <alex@example.com>", subject="Hallo",
              body="Hallo Bot", msg_id="<m1@example.com>") -> bytes:
    m = EmailMessage()
    m["From"] = from_
    m["To"] = "bot@myhive.de"
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
        return ("OK", [b"1"])

    def search(self, charset, *criteria):
        ids = " ".join(str(i + 1) for i in range(len(self._raws)))
        return ("OK", [ids.encode()])

    def fetch(self, mid, parts):
        idx = int(mid) - 1
        return ("OK", [(b"x", self._raws[idx])])

    def logout(self):
        pass


def _patch_imap(monkeypatch, raws):
    from hydrahive.communication.mail import imap_poll
    monkeypatch.setattr(imap_poll.imaplib, "IMAP4_SSL",
                        lambda host, port: _FakeIMAP(raws))


def test_poll_unseen_parses_message(monkeypatch):
    from hydrahive.communication.mail import imap_poll
    _patch_imap(monkeypatch, [_raw_mail()])
    cfg = {"imap_host": "imap.x", "imap_user": "bot@myhive.de", "imap_password": "pw"}
    mails = imap_poll.poll_unseen(cfg, "INBOX", set())
    assert len(mails) == 1
    m = mails[0]
    assert m.from_addr == "alex@example.com"
    assert m.from_name == "Alex"
    assert m.subject == "Hallo"
    assert "Hallo Bot" in m.body
    assert m.message_id == "<m1@example.com>"


def test_poll_unseen_dedups_seen(monkeypatch):
    from hydrahive.communication.mail import imap_poll
    _patch_imap(monkeypatch, [_raw_mail(msg_id="<dup@x>")])
    cfg = {"imap_host": "imap.x", "imap_user": "u", "imap_password": "pw"}
    mails = imap_poll.poll_unseen(cfg, "INBOX", {"<dup@x>"})
    assert mails == []


def test_poll_unseen_unconfigured_returns_empty():
    from hydrahive.communication.mail import imap_poll
    assert imap_poll.poll_unseen({}, "INBOX", set()) == []


# ---------------------------------------------------------------- Verarbeitung

def _msg(**kw):
    from hydrahive.communication.mail import imap_poll
    base = dict(message_id="<m1@x>", from_addr="alex@example.com", from_name="Alex",
                to="bot@myhive.de", subject="Frage", date="", body="Wie spät?")
    base.update(kw)
    return imap_poll.MailMessage(**base)


def test_process_sends_reply_with_re_subject(monkeypatch):
    from hydrahive.communication.mail import watcher

    async def fake_handle(event):
        assert event.channel == "email"
        assert event.metadata.get("is_owner") is False   # Fremder → Datenschutz greift
        assert event.external_user_id == "alex@example.com"
        return "Hallo Alex, hier ist die Antwort."

    sent = {}

    def fake_send(cfg, *, to, subject, body, in_reply_to=None):
        sent.update(to=to, subject=subject, body=body, in_reply_to=in_reply_to)

    monkeypatch.setattr(watcher, "handle_incoming", fake_handle)
    monkeypatch.setattr(watcher.smtp_send, "send_reply", fake_send)

    asyncio.run(watcher._process(_msg(), {"smtp_from": "bot@myhive.de"}))

    assert sent["to"] == "alex@example.com"
    assert sent["subject"] == "Re: Frage"
    assert sent["in_reply_to"] == "<m1@x>"
    assert "Antwort" in sent["body"]


def test_process_keeps_existing_re_prefix(monkeypatch):
    from hydrahive.communication.mail import watcher

    async def fake_handle(event):
        return "ok"

    sent = {}
    monkeypatch.setattr(watcher, "handle_incoming", fake_handle)
    monkeypatch.setattr(watcher.smtp_send, "send_reply",
                        lambda cfg, **kw: sent.update(kw))

    asyncio.run(watcher._process(_msg(subject="Re: Frage"), {"smtp_from": "bot@myhive.de"}))
    assert sent["subject"] == "Re: Frage"   # kein doppeltes "Re: Re:"


def test_process_skips_self_mail(monkeypatch):
    from hydrahive.communication.mail import watcher

    called = {"handle": False, "send": False}

    async def fake_handle(event):
        called["handle"] = True
        return "x"

    monkeypatch.setattr(watcher, "handle_incoming", fake_handle)
    monkeypatch.setattr(watcher.smtp_send, "send_reply",
                        lambda cfg, **kw: called.update(send=True))

    asyncio.run(watcher._process(_msg(from_addr="bot@myhive.de"), {"smtp_from": "bot@myhive.de"}))
    assert called["handle"] is False         # Loop-Schutz: keine Antwort an sich selbst
    assert called["send"] is False


def test_process_no_reply_when_agent_silent(monkeypatch):
    from hydrahive.communication.mail import watcher

    async def fake_handle(event):
        return None

    sent = {"called": False}
    monkeypatch.setattr(watcher, "handle_incoming", fake_handle)
    monkeypatch.setattr(watcher.smtp_send, "send_reply",
                        lambda cfg, **kw: sent.update(called=True))

    asyncio.run(watcher._process(_msg(), {"smtp_from": "bot@myhive.de"}))
    assert sent["called"] is False
