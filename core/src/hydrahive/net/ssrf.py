"""Zentraler SSRF-Schutz für ausgehende Requests.

Genutzt vom fetch_url-Tool und der butler http_post-Action. Blockt Loopback,
RFC1918, Link-Local und Cloud-Metadata. Hostnames werden per DNS aufgelöst und
ALLE resultierenden IPs geprüft — unmittelbar vor dem Connect aufrufen, dann
greift der Schutz auch gegen DNS-Rebinding.
"""
from __future__ import annotations

import ipaddress
import socket
import urllib.parse

import httpx

ALLOWED_SCHEMES = {"http", "https"}


class SsrfBlocked(Exception):
    """Outbound-Request wurde vom SSRF-Guard abgelehnt. ``args[0]`` = kurze Begründung."""

# Interne IP-Ranges blockieren
BLOCKED_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

# Hostnames die direkt geblockt werden (ohne DNS-Lookup)
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.internal",
    "169.254.169.254",  # AWS/GCP/Azure Metadaten-IP als String
}


def _ip_is_internal(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True, wenn die IP nicht öffentlich erreichbar sein darf.

    Normalisiert IPv4-mapped-IPv6 (``::ffff:127.0.0.1`` → ``127.0.0.1``) und blockt
    zusätzlich zu den expliziten BLOCKED_RANGES alles Nicht-Globale: Loopback,
    RFC1918, Link-Local, unspecified (``0.0.0.0``), CGNAT, reserviert.
    """
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not ip.is_global or any(ip in net for net in BLOCKED_RANGES)


def is_blocked_host(hostname: str) -> bool:
    """Prüft ob ein Hostname auf eine interne/gesperrte Adresse zeigt.

    Drei Stufen: Hostname-Denylist → direktes IP-Parse → DNS-Auflösung.
    """
    if not hostname:
        return True
    normalized = hostname.lower().strip(".")
    if normalized in BLOCKED_HOSTNAMES:
        return True
    try:
        ip = ipaddress.ip_address(hostname)
        return _ip_is_internal(ip)
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        for info in infos:
            addr = info[4][0]
            try:
                if _ip_is_internal(ipaddress.ip_address(addr)):
                    return True
            except ValueError:
                pass
    except OSError:
        pass
    return False


def validate_outbound_url(url: str) -> str | None:
    """None wenn die URL gefahrlos angefragt werden darf, sonst kurze Begründung.

    Prüft Scheme-Allowlist (http/https) und blockt interne Hosts/IPs.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return "scheme_not_allowed"
    if not parsed.hostname:
        return "host_missing"
    if is_blocked_host(parsed.hostname):
        return "host_blocked"
    return None


def resolve_validated_ip(hostname: str) -> str:
    """Löst ``hostname`` EINMAL auf und gibt eine validierte IP zurück.

    Der Rückgabewert wird beim Connect gepinnt (siehe ``safe_async_client``), sodass
    die geprüfte Auflösung auch die verbundene ist — das schließt DNS-Rebinding (TOCTOU).
    Blockt, wenn der Hostname auf der Denylist steht oder IRGENDEINE aufgelöste IP
    intern ist (Multi-A-Record-Bypass). Wirft ``SsrfBlocked``.
    """
    if not hostname:
        raise SsrfBlocked("host_missing")
    if hostname.lower().strip(".") in BLOCKED_HOSTNAMES:
        raise SsrfBlocked("host_blocked")
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None:
        if _ip_is_internal(literal):
            raise SsrfBlocked("host_blocked")
        return str(literal)
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except OSError as e:
        raise SsrfBlocked("dns_failed") from e
    validated: list[str] = []
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _ip_is_internal(ip):
            raise SsrfBlocked("host_blocked")
        validated.append(str(ip))
    if not validated:
        raise SsrfBlocked("dns_empty")
    return validated[0]


def pin_request(request: httpx.Request, host_to_ip: dict[str, str]) -> httpx.Request:
    """Pinnt die Verbindung an eine vorab validierte IP.

    Schreibt ``url.host`` auf die IP um (TCP-Connect geht dorthin, kein erneuter
    DNS-Lookup), behält aber SNI-Hostname und Host-Header auf dem Original-Namen,
    damit TLS-Zertifikatsprüfung und Server-Routing korrekt bleiben.
    """
    host = request.url.host
    ip = host_to_ip.get(host)
    if ip and host != ip:
        port = request.url.port
        request.headers["Host"] = host if port is None else f"{host}:{port}"
        request.extensions = {**request.extensions, "sni_hostname": host}
        request.url = request.url.copy_with(host=ip)
    return request


class _PinnedTransport(httpx.AsyncHTTPTransport):
    """AsyncHTTPTransport, der ausgehende Requests an vorab validierte IPs pinnt."""

    def __init__(self, host_to_ip: dict[str, str], **kwargs) -> None:
        super().__init__(**kwargs)
        self._pin = dict(host_to_ip)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        pin_request(request, self._pin)
        return await super().handle_async_request(request)


def safe_async_client(url: str, *, timeout: float) -> httpx.AsyncClient:
    """``httpx.AsyncClient``, dessen Verbindung zum Host von ``url`` an eine vorab
    validierte IP gepinnt ist (DNS-Rebinding-sicher). Wirft ``SsrfBlocked`` bevor
    irgendeine Verbindung aufgebaut wird. Redirects sind aus (ein 30x auf eine
    interne URL würde den Check sonst umgehen)."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise SsrfBlocked("scheme_not_allowed")
    if not parsed.hostname:
        raise SsrfBlocked("host_missing")
    ip = resolve_validated_ip(parsed.hostname)
    transport = _PinnedTransport({parsed.hostname: ip})
    return httpx.AsyncClient(timeout=timeout, follow_redirects=False, transport=transport)
