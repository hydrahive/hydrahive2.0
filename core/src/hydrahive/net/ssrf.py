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

ALLOWED_SCHEMES = {"http", "https"}

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
        return any(ip in net for net in BLOCKED_RANGES)
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        for info in infos:
            addr = info[4][0]
            try:
                if any(ipaddress.ip_address(addr) in net for net in BLOCKED_RANGES):
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
