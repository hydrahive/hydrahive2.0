"""Mailversand/-empfang des Kerns prüft TLS-Zertifikate (Task e6a2e5c2, Befund 24.10.2026).

Vorher: starttls()/SMTP_SSL/IMAP4_SSL ohne SSL-Kontext → smtplib/imaplib nehmen ssl._create_stdlib_context()
(CERT_NONE, kein Hostname-Abgleich). Jeder im Netz konnte sich dazwischenschalten und das Mail-Passwort mitlesen.
Jetzt: geprüfter Kontext (Zertifikat + Hostname, TLS ≥ 1.2). Nur mit ausdrücklicher Einstellung „Zertifikat nicht
prüfen“ (Standard aus) für eigene Testserver mit selbstsigniertem Zertifikat.
"""
from __future__ import annotations

import datetime
import socket
import ssl
import threading
from email.message import EmailMessage

import pytest


def _ctx_ok(ctx) -> bool:
    return (isinstance(ctx, ssl.SSLContext) and ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
            and ctx.minimum_version >= ssl.TLSVersion.TLSv1_2)


class _Rec:
    """Gefälschte smtplib-Klasse, merkt sich den übergebenen Kontext."""
    made: list = []

    def __init__(self, host, port, timeout=None, context=None):
        self.ctx_init, self.ctx_tls, self.calls = context, None, []
        type(self).made.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def ehlo(self):
        pass

    def starttls(self, context=None):
        self.ctx_tls = context

    def login(self, u, p):
        pass

    def send_message(self, m):
        self.calls.append("send")


def _msg():
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = "a@x.de", "b@y.de", "t"
    m.set_content("x")
    return m


@pytest.fixture
def rec(monkeypatch):
    from hydrahive.communication.mail import _transport

    class Plain(_Rec):
        made = []

    class SSL_(_Rec):
        made = []
    monkeypatch.setattr(_transport.smtplib, "SMTP", Plain)
    monkeypatch.setattr(_transport.smtplib, "SMTP_SSL", SSL_)
    return Plain, SSL_


def test_starttls_mit_gepruefem_kontext(rec):
    from hydrahive.communication.mail import _transport
    plain, _ = rec
    _transport.send_message({"host": "smtp.x.de", "port": 587, "use_tls": True}, _msg())
    assert _ctx_ok(plain.made[0].ctx_tls)


def test_implizites_ssl_mit_gepruefem_kontext(rec):
    from hydrahive.communication.mail import _transport
    _, ssl_ = rec
    _transport.send_message({"host": "smtp.x.de", "port": 465}, _msg())
    assert _ctx_ok(ssl_.made[0].ctx_init)


def test_unsicher_nur_mit_ausdruecklicher_einstellung(rec, monkeypatch):
    from hydrahive.communication.mail import _tls, _transport
    plain, ssl_ = rec
    monkeypatch.setattr(_tls, "insecure_allowed", lambda: True)
    _transport.send_message({"host": "mail.lan", "port": 587, "use_tls": True}, _msg())
    _transport.send_message({"host": "mail.lan", "port": 465}, _msg())
    for c in (plain.made[0].ctx_tls, ssl_.made[0].ctx_init):
        assert c.verify_mode == ssl.CERT_NONE and not c.check_hostname
        assert c.minimum_version >= ssl.TLSVersion.TLSv1_2, "auch unsicher kein altes TLS"


def test_einstellung_standard_aus_und_in_systemeinstellungen():
    from hydrahive.communication.mail import _tls
    from hydrahive.settings.editable import BY_KEY
    assert _tls.insecure_allowed() is False
    s = BY_KEY["mail_tls_insecure"]
    assert s.type == "bool" and s.default in ("", "0", "false") and "unsicher" in s.label.lower()


def test_imap_mit_gepruefem_kontext(monkeypatch):
    from hydrahive.communication.mail import imap_poll
    seen = {}

    class FakeIMAP:
        def __init__(self, host, port, ssl_context=None, timeout=None):
            seen["ctx"] = ssl_context

        def login(self, u, p):
            raise imap_poll.imaplib.IMAP4.error("stop")

        def logout(self):
            pass
    monkeypatch.setattr(imap_poll.imaplib, "IMAP4_SSL", FakeIMAP)
    imap_poll.fetch({"imap_host": "imap.x.de", "imap_user": "u", "imap_password": "p"}, "INBOX")
    assert _ctx_ok(seen["ctx"])


# ---- echter TLS-Handshake: selbstsigniertes Zertifikat wird abgelehnt ----

def _selfsigned(tmp_path):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(1).not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
            .sign(key, hashes.SHA256()))
    c, k = tmp_path / "c.pem", tmp_path / "k.pem"
    c.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    k.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.NoEncryption()))
    return c, k


@pytest.fixture
def evil_smtp(tmp_path):
    """SMTP auf 127.0.0.1 mit STARTTLS und selbstsigniertem Zertifikat – wie ein Angreifer im Netz."""
    crt, key = _selfsigned(tmp_path)
    sctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    sctx.load_cert_chain(crt, key)
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(2)
    got = {"auth": False, "mail": False}

    def serve():
        try:
            c, _ = srv.accept()
        except OSError:
            return
        f = c.makefile("rb")
        say = lambda s, sock=c: sock.sendall((s + "\r\n").encode())  # noqa: E731
        say("220 evil")
        sock = c
        while True:
            line = f.readline()
            if not line:
                break
            u = line.decode(errors="replace").strip().upper()
            if u.startswith("EHLO"):
                say("250-evil\r\n250-STARTTLS\r\n250 AUTH PLAIN", sock)
            elif u == "STARTTLS":
                say("220 go", sock)
                try:
                    sock = sctx.wrap_socket(sock, server_side=True)
                except (ssl.SSLError, OSError):
                    break
                f = sock.makefile("rb")
            elif u.startswith("AUTH"):
                got["auth"] = True
                say("235 ok", sock)
            elif u.startswith("MAIL"):
                got["mail"] = True
                say("250 ok", sock)
            else:
                say("250 ok", sock)
        c.close()
    threading.Thread(target=serve, daemon=True).start()
    yield srv.getsockname()[1], got
    srv.close()


def test_selbstsigniert_abgelehnt_kein_passwort_gesendet(evil_smtp):
    from hydrahive.communication.mail import _transport
    port, got = evil_smtp
    with pytest.raises(ssl.SSLCertVerificationError):
        _transport.send_message({"host": "localhost", "port": port, "use_tls": True, "user": "u",
                                 "password": "geheim"}, _msg())
    assert got == {"auth": False, "mail": False}, "Passwort und Mail gehen nie an einen ungeprüften Server"


def test_verstaendlicher_hinweis_bei_zertifikatsfehler():
    from hydrahive.communication.mail import _tls
    e = ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] self-signed certificate")
    h = _tls.hint(e)
    assert h and "Zertifikat" in h and "Einstellungen" in h and "Mail" in h
    assert _tls.hint(TimeoutError("x")) is None and _tls.hint(OSError("y")) is None


def test_send_mail_tool_zeigt_hinweis(monkeypatch):
    import asyncio
    from pathlib import Path

    from hydrahive.communication.mail import _transport
    from hydrahive.tools import send_mail
    from hydrahive.tools.base import ToolContext

    def boom(cfg, msg):
        raise ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] self-signed certificate")
    monkeypatch.setattr(_transport, "send_message", boom)
    ctx = ToolContext(session_id="s", agent_id="a", user_id="u", workspace=Path("/tmp"),
                      config={"smtp": {"host": "smtp.x.de", "port": 587, "from": "bot@x.de"}})
    r = asyncio.run(send_mail._execute({"to": "b@y.de", "subject": "t", "body": "x"}, ctx))
    assert not r.success and "Zertifikat" in (r.error or "")


def test_read_mail_meldet_zertifikatsfehler_statt_keine_nachrichten(monkeypatch):
    import asyncio
    from pathlib import Path

    from hydrahive.communication.mail import imap_poll
    from hydrahive.tools import read_mail
    from hydrahive.tools.base import ToolContext

    def boom(*a, **kw):
        raise ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] self-signed certificate")
    monkeypatch.setattr(imap_poll.imaplib, "IMAP4_SSL", boom)
    ctx = ToolContext(session_id="s", agent_id="a", user_id="u", workspace=Path("/tmp"),
                      config={"imap": {"host": "imap.x.de", "user": "u", "password": "p"}})
    r = asyncio.run(read_mail._execute({}, ctx))
    assert not r.success and "Zertifikat" in (r.error or "")


def test_watcher_laeuft_weiter_und_imap_fehler_bleiben_verschluckt(monkeypatch):
    from hydrahive.communication.mail import imap_poll

    def other(*a, **kw):
        raise OSError("Netz weg")
    monkeypatch.setattr(imap_poll.imaplib, "IMAP4_SSL", other)
    assert imap_poll.fetch({"imap_host": "h", "imap_user": "u", "imap_password": "p"}, "INBOX") == []
