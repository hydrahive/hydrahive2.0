from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

CredentialType = Literal["bearer", "basic", "cookie", "header", "query"]
ALL_TYPES: tuple[CredentialType, ...] = ("bearer", "basic", "cookie", "header", "query")

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


def matches_url(pattern: str, url: str) -> bool:
    """Einfacher Glob-Match: `*` matcht alles, sonst regex aus glob übersetzen."""
    if not pattern or pattern == "*":
        return True
    # `*` zu `.*`, alles andere escapen
    parts = re.split(r"(\*)", pattern)
    rx = "".join(".*" if p == "*" else re.escape(p) for p in parts)
    return bool(re.match(f"^{rx}$", url))
