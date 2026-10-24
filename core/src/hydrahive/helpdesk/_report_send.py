"""Fehlerbericht senden (docs/plans/help-error-report.md): über das eingetragene Mailkonto der Installation
(System → Einstellungen → Mail, derselbe Weg wie send_mail) an die feste Adresse. Ohne Mailkonto: mailto-Daten,
damit der Nutzer den fertigen Bericht in seinem Mailprogramm abschickt. Keine Zugangsdaten im Code.
"""
from __future__ import annotations

from email.message import EmailMessage
from urllib.parse import quote

from hydrahive.helpdesk import _report

MAILTO_MAX = 1800          # viele Mailprogramme/Browser kappen längere mailto-Links


class SendFailed(RuntimeError):
    pass


def _smtp() -> dict:
    from hydrahive.tools.send_mail import _settings_smtp
    return _settings_smtp()


def has_mail_account() -> bool:
    cfg = _smtp()
    return bool(cfg.get("host") and cfg.get("from"))


def mailto(report: dict) -> dict:
    to = _report.recipient()
    body = report["body"]
    head = f"mailto:{to}?subject={quote(report['subject'])}&body="
    truncated = False
    while len(head) + len(quote(body)) > MAILTO_MAX and len(body) > 200:
        body = body[: int(len(body) * 0.8)]
        truncated = True
    if truncated:
        body += "\n\n[gekürzt – vollständigen Text bitte aus dem Hilfe-Fenster einfügen]"
    return {"sent": False, "reason": "no_mail_account", "to": to, "mailto": head + quote(body),
            "truncated": truncated, "subject": report["subject"], "body": report["body"]}


def send(report: dict) -> dict:
    """Mail verschicken oder mailto-Daten liefern. Wirft SendFailed (ohne Zugangsdaten im Text)."""
    if not has_mail_account():
        return mailto(report)
    cfg = _smtp()
    msg = EmailMessage()
    msg["From"] = cfg["from"]
    msg["To"] = _report.recipient()
    msg["Subject"] = report["subject"]
    msg["X-HydraHive-Report"] = report["id"]
    msg.set_content(report["body"])
    from hydrahive.communication.mail import _transport
    try:
        _transport.send_message(cfg, msg)
    except Exception as e:  # noqa: BLE001 - jede Störung → Fehlermeldung ohne Passwort, Entwurf bleibt
        from hydrahive.credentials.redaction import scrub
        raise SendFailed(scrub(f"{type(e).__name__}: {e}", {cfg.get("password") or ""} - {""})[:300]) from None
    return {"sent": True, "to": _report.recipient()}
