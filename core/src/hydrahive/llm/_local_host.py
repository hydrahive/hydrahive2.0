"""Erkennt, ob ein Hostname auf DIESE Maschine zeigt.

Gebraucht für llmfit: das Werkzeug misst immer die Hardware des Rechners, auf
dem HydraHive läuft. Diese Zahlen dürfen nur dann einem Ollama-Endpunkt
zugeordnet werden, wenn dieser Endpunkt tatsächlich hier läuft — sonst würde
der Katalog die Hardware des falschen Rechners anzeigen.

Loopback allein reicht als Prüfung nicht: Eine Workstation trägt ihren
Ollama-Endpunkt üblicherweise unter der eigenen LAN-IP ein (z.B.
http://192.168.178.197:11434), nicht unter localhost. Ohne die lokalen
Adressen zu kennen, hielte HydraHive den eigenen Rechner für einen fremden.
"""
from __future__ import annotations

import functools
import ipaddress
import logging
import socket

logger = logging.getLogger(__name__)

_LOOPBACK_NAMES = {"localhost", "127.0.0.1", "::1", "ip6-localhost", "ip6-loopback"}


def _own_addresses() -> frozenset[str]:
    """Alle IP-Adressen dieses Hosts, normalisiert als Strings.

    Best effort: Schlägt die Auflösung fehl (kein DNS, kein Netz), liefert die
    Funktion eine leere Menge. Der Aufrufer fällt dann auf die reine
    Loopback-Prüfung zurück — lieber kein Fit als ein falscher.
    """
    found: set[str] = set()
    try:
        hostname = socket.gethostname()
    except OSError:
        return frozenset()
    for name in {hostname, f"{hostname}.local"}:
        try:
            infos = socket.getaddrinfo(name, None)
        except (OSError, UnicodeError):
            continue
        for info in infos:
            address = info[4][0]
            if isinstance(address, str):
                found.add(_normalize(address))
    return frozenset(found)


@functools.lru_cache(maxsize=1)
def _cached_own_addresses() -> frozenset[str]:
    """Adressen einmal auflösen. Ändert sich die IP, greift ein Neustart.

    Bewusst gecacht: catalog_overview läuft bei jedem Katalogaufruf, und
    getaddrinfo kann bei kaputtem DNS in einen Timeout laufen.
    """
    return _own_addresses()


def _normalize(value: str) -> str:
    """IPv6-Zonen entfernen und Adressen kanonisch schreiben."""
    cleaned = value.split("%", 1)[0].strip().strip("[]").lower()
    try:
        return str(ipaddress.ip_address(cleaned))
    except ValueError:
        return cleaned


def is_local_host(hostname: str | None) -> bool:
    """True, wenn `hostname` auf diese Maschine zeigt.

    Erkennt Loopback, jede unspezifizierte Adresse (0.0.0.0/::) sowie alle
    IP-Adressen, unter denen dieser Host selbst erreichbar ist.
    """
    if not hostname:
        return False
    candidate = _normalize(hostname)
    if candidate in _LOOPBACK_NAMES:
        return True
    try:
        parsed = ipaddress.ip_address(candidate)
    except ValueError:
        # Kein IP-Literal: nur der eigene Rechnername zählt, nichts anderes.
        try:
            own_name = socket.gethostname().lower()
        except OSError:
            return False
        return candidate in {own_name, own_name.split(".", 1)[0], f"{own_name}.local"}
    if parsed.is_loopback or parsed.is_unspecified:
        return True
    return candidate in _cached_own_addresses()


def _cache_clear() -> None:
    _cached_own_addresses.cache_clear()
