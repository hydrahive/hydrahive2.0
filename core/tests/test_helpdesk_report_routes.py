"""Fehlerbericht – Routen und Versand (docs/plans/help-error-report.md).

Senden nur über die Route (Klick des Nutzers), über das eingetragene Mailkonto der Installation an die feste Adresse.
Ohne Mailkonto: mailto-Daten statt Versand. Fremder Entwurf = 404, einmal sendbar, Grenzen, Schalter.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

B = "/api/helpdesk/report"


@pytest.fixture(autouse=True)
def _clean(setup_test_env, monkeypatch):
    from hydrahive.helpdesk import _report
    _report._DRAFTS.clear()
    _report._SENT.clear()
    yield
    _report._DRAFTS.clear()
    _report._SENT.clear()


@pytest.fixture
def sent(monkeypatch):
    """Mail-Transport als Attrappe; Mailkonto der Installation eingetragen."""
    from hydrahive.communication.mail import _transport
    from hydrahive.helpdesk import _report_send
    out = []
    monkeypatch.setattr(_transport, "send_message", lambda cfg, msg: out.append((cfg, msg)))
    monkeypatch.setattr(_report_send, "_smtp", lambda: {"host": "smtp.firma.example", "port": 587, "user": "hh",
                                                        "password": "pw", "from": "hydrahive@firma.example",
                                                        "use_tls": True})
    return out


@pytest.fixture
def no_mail(monkeypatch):
    from hydrahive.helpdesk import _report_send
    monkeypatch.setattr(_report_send, "_smtp", lambda: {"host": "", "from": ""})


def _draft(user="testuser", text="Knopf geht nicht"):
    from hydrahive.helpdesk import _report
    return _report.prepare(user, text, "/mailbox")


def test_senden_ueber_mailkonto(client, auth_headers, sent):
    d = _draft()
    r = client.post(f"{B}/{d['id']}/send", headers=auth_headers)
    assert r.status_code == 200 and r.json() == {"sent": True, "to": "issue@hydrahive.org"}
    cfg, msg = sent[0]
    assert msg["To"] == "issue@hydrahive.org" and msg["From"] == "hydrahive@firma.example"
    assert msg["Subject"] == d["subject"] and "Knopf geht nicht" in msg.get_content()
    assert client.post(f"{B}/{d['id']}/send", headers=auth_headers).status_code == 404, "einmal sendbar"


def test_ohne_mailkonto_mailto(client, auth_headers, no_mail):
    d = _draft()
    r = client.post(f"{B}/{d['id']}/send", headers=auth_headers)
    assert r.status_code == 200
    j = r.json()
    assert j["sent"] is False and j["reason"] == "no_mail_account"
    u = urlsplit(j["mailto"])
    assert u.scheme == "mailto" and u.path == "issue@hydrahive.org"
    q = parse_qs(u.query)
    assert q["subject"] == [d["subject"]] and "Knopf geht nicht" in q["body"][0]
    assert j["body"] == d["body"], "voller Text zum Kopieren"
    assert client.post(f"{B}/{d['id']}/send", headers=auth_headers).status_code == 404


def test_ansehen_ohne_mailkonto_liefert_mailto_und_entwurf_bleibt(client, auth_headers, no_mail):
    d = _draft()
    j = client.get(f"{B}/{d['id']}", headers=auth_headers).json()
    assert j["mailto"].startswith("mailto:issue@hydrahive.org?subject=") and j["truncated"] is False
    assert client.get(f"{B}/{d['id']}", headers=auth_headers).status_code == 200, "Ansehen verbraucht nichts"


def test_ansehen_mit_mailkonto_ohne_mailto(client, auth_headers, sent):
    assert "mailto" not in client.get(f"{B}/{_draft()['id']}", headers=auth_headers).json()


def test_langer_text_im_mailto_gekuerzt(client, auth_headers, no_mail):
    from hydrahive.helpdesk import _report_send
    d = _draft(text="x" * 1000)
    j = client.post(f"{B}/{d['id']}/send", headers=auth_headers).json()
    assert len(j["mailto"]) <= _report_send.MAILTO_MAX + 200 and j["truncated"] in (True, False)


def test_fremder_entwurf_404(client, admin_headers, sent):
    d = _draft("testuser")
    assert client.get(f"{B}/{d['id']}", headers=admin_headers).status_code == 404
    assert client.post(f"{B}/{d['id']}/send", headers=admin_headers).status_code == 404
    assert sent == []


def test_ansehen_und_verwerfen(client, auth_headers, sent):
    d = _draft()
    r = client.get(f"{B}/{d['id']}", headers=auth_headers)
    assert r.json() == {"id": d["id"], "subject": d["subject"], "body": d["body"], "to": "issue@hydrahive.org"}
    assert client.delete(f"{B}/{d['id']}", headers=auth_headers).status_code == 204
    assert client.post(f"{B}/{d['id']}/send", headers=auth_headers).status_code == 404 and sent == []


def test_grenze_429(client, auth_headers, sent):
    from hydrahive.helpdesk import _report
    for _ in range(_report.PER_USER_HOUR):
        assert client.post(f"{B}/{_draft()['id']}/send", headers=auth_headers).status_code == 200
    d = _draft()
    r = client.post(f"{B}/{d['id']}/send", headers=auth_headers)
    assert r.status_code == 429 and len(sent) == _report.PER_USER_HOUR
    assert client.get(f"{B}/{d['id']}", headers=auth_headers).status_code == 200, "Entwurf bleibt erhalten"


def test_versand_fehler_entwurf_bleibt(client, auth_headers, monkeypatch, sent):
    from hydrahive.communication.mail import _transport

    def boom(cfg, msg):
        raise OSError("Verbindung abgelehnt")
    monkeypatch.setattr(_transport, "send_message", boom)
    d = _draft()
    r = client.post(f"{B}/{d['id']}/send", headers=auth_headers)
    assert r.status_code == 502 and "pw" not in r.text
    assert client.get(f"{B}/{d['id']}", headers=auth_headers).status_code == 200


def test_schalter_aus(client, auth_headers, sent, monkeypatch):
    from hydrahive.helpdesk import _report
    d = _draft()
    monkeypatch.setattr(_report, "enabled", lambda: False)
    r = client.post(f"{B}/{d['id']}/send", headers=auth_headers)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "error_report_disabled" and sent == []


def test_ohne_login_401(client):
    assert client.post(f"{B}/x/send").status_code == 401


def test_status_fuer_fenster(client, auth_headers, admin_headers, no_mail):
    r = client.get(f"{B}-status", headers=auth_headers).json()
    assert r == {"enabled": True, "mail_account": False, "can_setup": False}
    assert client.get(f"{B}-status", headers=admin_headers).json()["can_setup"] is True


def test_schalter_in_den_systemeinstellungen(client, admin_headers):
    keys = {s["key"]: s for s in client.get("/api/system/settings", headers=admin_headers).json()["settings"]}
    assert keys["help_error_report_enabled"]["type"] == "bool"
