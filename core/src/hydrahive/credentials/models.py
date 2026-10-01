from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from typing import Literal

CredentialType = Literal["bearer", "basic", "cookie", "header", "query", "ssh_key"]
ALL_TYPES: tuple[CredentialType, ...] = ("bearer", "basic", "cookie", "header", "query", "ssh_key")

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")


@dataclass
class Credential:
    name: str
    type: CredentialType
    value: str
    url_pattern: str = "*"  # einfacher Glob: "*" oder "https://*.example.com/*"
    description: str = ""
    header_name: str = ""   # nur bei type="header": Header-Name (z.B. "X-Api-Key")
    query_param: str = ""   # nur bei type="query": Query-Param-Name (z.B. "api_key")


def is_valid_name(name: str) -> bool:
    return bool(NAME_RE.match(name))


# Trenner zwischen Authority (Host[:Port]) und Pfad/Query/Fragment.
_AUTHORITY_END = re.compile(r"[/?#]")
_WS_OR_CTRL = re.compile(r"[\x00-\x20\x7f]")
# Zeichen, die in einem Hostnamen vorkommen dürfen (IPv6 ohne Klammern: ":").
_HOST_CHARS = re.compile(r"[A-Za-z0-9.\-:_]+")


def _glob(glob: str, text: str, *, ignore_case: bool = False) -> bool:
    rx = "".join(".*" if p == "*" else re.escape(p) for p in re.split(r"(\*)", glob))
    return re.fullmatch(rx, text, re.IGNORECASE if ignore_case else 0) is not None


def _split_pattern(pattern: str) -> tuple[str, str, str, str]:
    """Muster mit "://" → (Schema-, Host-, Port-, Rest-Glob). Port "" = keiner."""
    scheme, after = pattern.split("://", 1)
    m = _AUTHORITY_END.search(after)
    authority, rest = (after[:m.start()], after[m.start():]) if m else (after, "")
    authority = authority.rsplit("@", 1)[-1]
    if authority.startswith("["):  # IPv6-Literal
        host, _, tail = authority[1:].partition("]")
        return scheme, host, tail[1:] if tail.startswith(":") else "", rest
    host, sep, port = authority.rpartition(":")
    if not sep or not (port.isdigit() or port == "*"):
        host, port = authority, ""
    return scheme, host, port, rest


def has_concrete_host(pattern: str) -> bool:
    """True, wenn das Muster an einen echten Host gebunden ist — nur dann wird ein
    Credential automatisch eingesetzt (Security-Task ef27f79b).

    Konkret: Schema-Teil vorhanden ("://") und der Host ist entweder ohne "*"
    (api.example.com, 192.168.1.20) oder genau "*." + Domain mit Punkt
    (*.example.com). Nicht konkret: "*", "https://*", "*://*/*", "https://*.com/*",
    "https://api.example.com*" oder Muster ohne Schema wie "*github.com*".
    """
    if "://" not in (pattern or ""):
        return False
    host = _split_pattern(pattern)[1]
    if host.startswith("*."):
        host = host[2:]
        if "." not in host:
            return False
    return "*" not in host and bool(re.search(r"[A-Za-z0-9]", host))


def matches_url(pattern: str, url: str) -> bool:
    """Glob-Match eines Credential-Musters gegen eine URL.

    - "" oder "*" passt auf alles (wird aber nie automatisch eingesetzt).
    - Muster mit "://" werden in Teile zerlegt: ein "*" im Host bleibt im Host
      (früher reichte es bis in den Pfad eines fremden Hosts:
      "https://*.example.com/*" passte auf "https://evil.com/.example.com/x").
      Host ohne Groß-/Kleinschreibung; ohne Port im Muster darf die URL keinen
      Port angeben; Pfad/Query als Glob wie bisher.
    - Muster ohne Schema (Altbestand): Glob über die ganze URL wie früher.
    """
    if not pattern or pattern == "*":
        return True
    if "://" not in pattern:
        return _glob(pattern, url)
    if _WS_OR_CTRL.search(url):
        # urllib entfernt Tab/Zeilenumbruch still, httpx lehnt sie ab — so eine URL
        # bekommt nie automatisch ein Secret.
        return False
    if "://" not in url:
        return False
    after = url.split("://", 1)[1]
    m = _AUTHORITY_END.search(after)
    authority = after[:m.start()] if m else after
    if "\\" in authority or "@" in authority:
        return False
    try:
        u = urllib.parse.urlsplit(url)
        u_host, u_port = u.hostname or "", u.port
    except ValueError:
        return False
    if not u_host or not _HOST_CHARS.fullmatch(u_host):
        return False
    u_rest = after[m.start():] if m else ""
    scheme, host, port, rest = _split_pattern(pattern)
    return (_glob(scheme, u.scheme, ignore_case=True)
            and _glob(host, u_host, ignore_case=True)
            and (_glob(port, str(u_port)) if port else u_port is None)
            and _glob(rest, u_rest))
