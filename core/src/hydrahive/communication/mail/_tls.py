"""TLS-Kontext für Mailversand und -empfang des Kerns (Task e6a2e5c2).

Ohne eigenen Kontext nehmen smtplib.starttls(), SMTP_SSL und imaplib.IMAP4_SSL ssl._create_stdlib_context():
kein Zertifikat, kein Hostname geprüft – jeder im Netz könnte sich dazwischenschalten und das Mail-Passwort lesen.
Hier: geprüft (Zertifikat + Hostname), mindestens TLS 1.2.

Nur wenn der Admin „Mail-Zertifikat nicht prüfen (unsicher)“ einschaltet (Standard aus) – für einen eigenen Server im
Heimnetz mit selbstsigniertem Zertifikat – wird die Prüfung abgeschaltet. TLS bleibt auch dann Pflicht (≥ 1.2).
"""
from __future__ import annotations

import ssl


def insecure_allowed() -> bool:
    from hydrahive.settings.overrides import env_or_override
    return env_or_override("mail_tls_insecure", "HH_MAIL_TLS_INSECURE", "false").strip().lower() \
        in ("1", "true", "yes", "on")


def context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    if insecure_allowed():
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def hint(exc: BaseException) -> str | None:
    """Verständlicher Hinweis, wenn der Mailserver ein ungültiges Zertifikat zeigt – sonst None."""
    if not isinstance(exc, ssl.SSLCertVerificationError):
        return None
    return ("Das Zertifikat des Mailservers ist ungültig oder selbstsigniert – HydraHive sendet dorthin aus "
            "Sicherheitsgründen kein Passwort. Prüfe Host-Namen und Zertifikat des Servers. Nur bei einem eigenen "
            "Server im Heimnetz: System → Einstellungen → Mail → „Zertifikat des Mailservers nicht prüfen (unsicher)“.")
