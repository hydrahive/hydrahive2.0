"""DNS-Rebinding-Schutz (TOCTOU) im SSRF-Guard — Issue #206 (Befund M6).

Die alten Tests prüfen nur statische interne Hosts. Hier: die Auflösung wird
EINMAL validiert und die Verbindung an die validierte IP gepinnt, sodass ein
zweiter (bösartiger) DNS-Lookup beim Connect nicht greifen kann.
"""
from __future__ import annotations

import socket

import httpx
import pytest

from hydrahive.net.ssrf import (
    SsrfBlocked,
    pin_request,
    resolve_validated_ip,
    safe_async_client,
)


def _gai(*ips):
    """Baut eine getaddrinfo-Antwort (Liste von 5-Tupeln) für die gegebenen IPs."""
    return [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 0))
        for ip in ips
    ]


# --- resolve_validated_ip: einmal auflösen, alle IPs prüfen -------------------

def test_resolve_returns_public_ip_with_single_lookup(monkeypatch):
    calls = {"n": 0}

    def fake(*a, **k):
        calls["n"] += 1
        return _gai("93.184.216.34")

    monkeypatch.setattr(socket, "getaddrinfo", fake)
    assert resolve_validated_ip("example.com") == "93.184.216.34"
    assert calls["n"] == 1  # genau EIN Lookup — der wird gepinnt


def test_resolve_blocks_internal_resolution(monkeypatch):
    # Der Rebinding-Fall: der Hostname löst auf eine interne IP auf.
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _gai("169.254.169.254"))
    with pytest.raises(SsrfBlocked):
        resolve_validated_ip("evil.example")


def test_resolve_blocks_if_any_record_internal(monkeypatch):
    # Multi-A-Record-Bypass: eine öffentliche + eine interne IP → blocken.
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _gai("93.184.216.34", "10.0.0.5"))
    with pytest.raises(SsrfBlocked):
        resolve_validated_ip("evil.example")


def test_resolve_literal_public_ip_skips_dns(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("Bei IP-Literal darf kein DNS-Lookup passieren")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    assert resolve_validated_ip("8.8.8.8") == "8.8.8.8"


def test_resolve_literal_internal_ip_blocked():
    with pytest.raises(SsrfBlocked):
        resolve_validated_ip("127.0.0.1")


def test_resolve_blocks_unspecified_address():
    # 0.0.0.0 routet auf vielen Systemen auf localhost — klassischer SSRF-Bypass.
    with pytest.raises(SsrfBlocked):
        resolve_validated_ip("0.0.0.0")


def test_resolve_blocks_ipv4_mapped_ipv6_loopback_literal():
    # ::ffff:127.0.0.1 ist Loopback, matcht aber keinen der IPv6-Blöcke direkt.
    with pytest.raises(SsrfBlocked):
        resolve_validated_ip("::ffff:127.0.0.1")


def test_resolve_blocks_ipv4_mapped_ipv6_via_dns(monkeypatch):
    # Bösartiger AAAA-Record, der intern auf Loopback zeigt.
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [
        (socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("::ffff:127.0.0.1", 0, 0, 0)),
    ])
    with pytest.raises(SsrfBlocked):
        resolve_validated_ip("sneaky.example")


# --- pin_request: Connect auf IP, SNI/Host auf Hostname ----------------------

def test_pin_request_rewrites_host_keeps_sni_and_host_header():
    req = httpx.Request("GET", "https://example.com/path")
    pin_request(req, {"example.com": "93.184.216.34"})
    assert req.url.host == "93.184.216.34"               # TCP-Connect auf IP
    assert req.extensions.get("sni_hostname") == "example.com"  # TLS bleibt korrekt
    assert req.headers["Host"] == "example.com"          # Server-Routing bleibt korrekt


def test_pin_request_noop_when_host_not_pinned():
    req = httpx.Request("GET", "https://other.example/path")
    pin_request(req, {"example.com": "93.184.216.34"})
    assert req.url.host == "other.example"
    assert "sni_hostname" not in req.extensions


# --- safe_async_client: Schema + interner Host blocken vor jedem Connect ------

def test_safe_async_client_rejects_non_http_scheme():
    with pytest.raises(SsrfBlocked):
        safe_async_client("ftp://example.com/x", timeout=5)


def test_safe_async_client_blocks_internal_host(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: _gai("10.0.0.5"))
    with pytest.raises(SsrfBlocked):
        safe_async_client("https://evil.example/x", timeout=5)
