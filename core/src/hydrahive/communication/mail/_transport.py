"""Gemeinsamer SMTP-Transport — Single Source für „wie verbinde ich mich".

Beide Sende-Pfade (das `send_mail`-Tool und die Watcher-Antwort) bauen nur die
`EmailMessage` und delegieren den Versand hierher. Der TLS-Modus wird aus dem
Port abgeleitet (IANA-Konvention):

- Port 465 → implizites SSL (TLS sofort, `smtplib.SMTP_SSL`)
- sonst    → STARTTLS wenn `use_tls` (Default), sonst Klartext

Damit kann Port 465 (z.B. KASserver/All-Inkl) nicht mehr mit STARTTLS-Logik
angesprochen werden — der häufigste Grund für Connection-Timeouts.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

_IMPLICIT_SSL_PORT = 465
_TIMEOUT = 30


def send_message(cfg: dict, msg: EmailMessage) -> None:
    host = cfg.get("host", "")
    port = int(cfg.get("port", 587))
    user = cfg.get("user")
    pw = cfg.get("password")

    if port == _IMPLICIT_SSL_PORT:
        with smtplib.SMTP_SSL(host, port, timeout=_TIMEOUT) as s:
            if user and pw:
                s.login(user, pw)
            s.send_message(msg)
        return

    with smtplib.SMTP(host, port, timeout=_TIMEOUT) as s:
        s.ehlo()
        if cfg.get("use_tls", True):
            s.starttls()
            s.ehlo()
        if user and pw:
            s.login(user, pw)
        s.send_message(msg)
