"""Fail-closed-Konfiguration und Origin-Allowlist des AI-Security-Moduls."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from hydrahive.settings import settings


class ConfigError(ValueError):
    """Die Betreiberkonfiguration ist ungültig."""


@dataclass(frozen=True)
class Target:
    origin: str


def _origin(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ConfigError("target_empty")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ConfigError("target_port_invalid") from exc
    if parsed.scheme not in {"http", "https"}:
        raise ConfigError("target_scheme_not_allowed")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ConfigError("target_host_invalid")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ConfigError("target_must_be_origin")
    host = parsed.hostname.lower().rstrip(".")
    if any(ch.isspace() for ch in host):
        raise ConfigError("target_host_invalid")
    if port is None:
        port = 80 if parsed.scheme == "http" else 443
    if not 1 <= port <= 65535:
        raise ConfigError("target_port_invalid")
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return urlunsplit((parsed.scheme, f"{host}:{port}", "", "", ""))


def configured_targets() -> tuple[Target, ...]:
    raw = settings.ai_security_targets
    if not raw:
        return ()
    values = tuple(_origin(item) for item in raw.split(","))
    if len(values) > 50:
        raise ConfigError("too_many_targets")
    return tuple(Target(origin=value) for value in dict.fromkeys(values))


def validate_target(raw: str) -> str:
    """Normalisiert ein Ziel und akzeptiert es nur bei exakter Betreiberfreigabe."""
    candidate = _origin(raw)
    if candidate not in {target.origin for target in configured_targets()}:
        raise ConfigError("target_not_allowed")
    return candidate
