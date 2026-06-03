"""Gemeinsamer SMTP-Transport: TLS-Modus aus Port ableiten.

Der Klassiker-Bug: Port 465 ist *implizites* SSL (TLS sofort), Port 587 ist
STARTTLS (erst Klartext, dann Upgrade). Wer 465 mit STARTTLS-Logik anspricht,
schickt Klartext-EHLO während der Server auf den TLS-Handshake wartet → Timeout.
Dieser Transport wählt die Verbindungsklasse anhand des Ports.

Lazy imports + gefälschte smtplib-Klassen, kein echtes Netz.
"""
from __future__ import annotations

from email.message import EmailMessage


class _FakeSMTP:
    """Zeichnet auf, was aufgerufen wurde — für SMTP und SMTP_SSL gleichermaßen."""
    last: "list[_FakeSMTP]" = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.timeout = host, port, timeout
        self.calls: list = []
        type(self).last.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self):
        self.calls.append("starttls")

    def login(self, user, pw):
        self.calls.append(("login", user, pw))

    def send_message(self, msg):
        self.calls.append("send")


def _patch(monkeypatch):
    from hydrahive.communication.mail import _transport

    class FakePlain(_FakeSMTP):
        last = []

    class FakeSSL(_FakeSMTP):
        last = []

    monkeypatch.setattr(_transport.smtplib, "SMTP", FakePlain)
    monkeypatch.setattr(_transport.smtplib, "SMTP_SSL", FakeSSL)
    return FakePlain, FakeSSL


def _msg():
    m = EmailMessage()
    m["From"] = "bot@x"
    m["To"] = "y@z"
    m["Subject"] = "Hi"
    m.set_content("yo")
    return m


def test_port_465_uses_implicit_ssl_no_starttls(monkeypatch):
    from hydrahive.communication.mail import _transport
    plain, ssl = _patch(monkeypatch)

    _transport.send_message(
        {"host": "w0.kasserver.com", "port": 465, "user": "u", "password": "p"}, _msg())

    assert len(ssl.last) == 1 and not plain.last        # SMTP_SSL genutzt, SMTP nicht
    assert "starttls" not in ssl.last[0].calls          # implizites SSL, kein STARTTLS
    assert ("login", "u", "p") in ssl.last[0].calls
    assert "send" in ssl.last[0].calls


def test_port_587_uses_starttls(monkeypatch):
    from hydrahive.communication.mail import _transport
    plain, ssl = _patch(monkeypatch)

    _transport.send_message(
        {"host": "w0.kasserver.com", "port": 587, "user": "u", "password": "p",
         "use_tls": True}, _msg())

    assert len(plain.last) == 1 and not ssl.last        # SMTP + STARTTLS
    assert "starttls" in plain.last[0].calls


def test_plain_when_tls_disabled(monkeypatch):
    from hydrahive.communication.mail import _transport
    plain, ssl = _patch(monkeypatch)

    _transport.send_message(
        {"host": "localhost", "port": 25, "use_tls": False}, _msg())

    assert len(plain.last) == 1 and not ssl.last
    assert "starttls" not in plain.last[0].calls


def test_login_skipped_without_credentials(monkeypatch):
    from hydrahive.communication.mail import _transport
    plain, ssl = _patch(monkeypatch)

    _transport.send_message({"host": "localhost", "port": 587, "use_tls": True}, _msg())

    assert not any(isinstance(c, tuple) and c[0] == "login" for c in plain.last[0].calls)
