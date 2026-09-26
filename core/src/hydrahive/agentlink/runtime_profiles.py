"""Bounded per-handoff runtime profiles for HydraHive-internal AgentLink tasks."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import quote

RUNTIME_METADATA_KEY = "agentlink_runtime"
RUNTIME_VERSION = 1
DEFAULT_RUNTIME_PROFILE = "standard"

_RESUME_TOKEN = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_PROFILE_CAPS: dict[str, tuple[int, int, int]] = {
    "quick": (8, 8_192, 180),
    "standard": (32, 16_384, 540),
    "deep": (96, 32_768, 1_800),
}


def _agent_defaults() -> tuple[int, int, int]:
    # Lazy import avoids the agents → validation → tools → ask_agent cycle.
    from hydrahive.agents._defaults import (
        DEFAULT_HANDOFF_TIMEOUT_SECONDS,
        DEFAULT_MAX_ITERATIONS,
        DEFAULT_MAX_TOKENS,
    )
    return DEFAULT_MAX_ITERATIONS, DEFAULT_MAX_TOKENS, DEFAULT_HANDOFF_TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class RuntimeBudget:
    version: int
    profile: str
    max_iterations: int
    max_tokens: int
    timeout_seconds: int

    def as_metadata(self) -> dict[str, int | str]:
        return asdict(self)


def normalize_profile(profile: object) -> str:
    value = profile.strip().lower() if isinstance(profile, str) else ""
    return value if value in _PROFILE_CAPS else DEFAULT_RUNTIME_PROFILE


def _validated_cap(value: Any, *, fallback: int, minimum: int, maximum: int) -> int:
    """Read persisted caps defensively without turning malformed values into grants."""
    if isinstance(value, bool):
        return fallback
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return fallback
    return parsed if minimum <= parsed <= maximum else fallback


def effective_budget(agent: dict, profile: object = DEFAULT_RUNTIME_PROFILE) -> RuntimeBudget:
    """Resolve a profile locally and intersect it with the target agent's caps."""
    selected = normalize_profile(profile)
    profile_iterations, profile_tokens, profile_timeout = _PROFILE_CAPS[selected]
    default_iterations, default_tokens, default_timeout = _agent_defaults()
    agent_iterations = _validated_cap(
        agent.get("max_iterations"), fallback=default_iterations,
        minimum=1, maximum=250,
    )
    agent_tokens = _validated_cap(
        agent.get("max_tokens"), fallback=default_tokens,
        minimum=1, maximum=200_000,
    )
    agent_timeout = _validated_cap(
        agent.get("handoff_timeout_seconds"),
        fallback=default_timeout,
        minimum=30, maximum=3_600,
    )
    return RuntimeBudget(
        version=RUNTIME_VERSION,
        profile=selected,
        max_iterations=min(profile_iterations, agent_iterations),
        max_tokens=min(profile_tokens, agent_tokens),
        timeout_seconds=min(profile_timeout, agent_timeout),
    )


def reason_with_profile(
    target_agent_id: str,
    profile: object,
    task_summary: str,
    *,
    resume_token: str | None = None,
) -> str:
    """Build the backward-compatible, versioned internal reason envelope."""
    selected = normalize_profile(profile)
    segments = [
        f"hh-target:{target_agent_id}",
        f"hh-runtime:v{RUNTIME_VERSION}:{selected}",
    ]
    if resume_token is not None:
        if not _RESUME_TOKEN.fullmatch(resume_token):
            raise ValueError("Ungültiges Resume-Token")
        segments.append(f"hh-resume:v{RUNTIME_VERSION}:{resume_token}")
    # Keep the human-readable reason while preventing task text from injecting
    # additional pipe-delimited control segments.
    encoded_summary = quote(" ".join(task_summary.split()), safe=" -_.")
    segments.append(f"hh-task: {encoded_summary}")
    return "|".join(segments)


def profile_from_reason(reason: str | None) -> str:
    """Extract a supported profile; old/unknown envelopes safely become standard."""
    for segment in (reason or "").split("|"):
        if segment.startswith("hh-task:"):
            break
        if not segment.startswith("hh-runtime:"):
            continue
        parts = segment.split(":", 2)
        if len(parts) != 3 or parts[1] != f"v{RUNTIME_VERSION}":
            return DEFAULT_RUNTIME_PROFILE
        return normalize_profile(parts[2])
    return DEFAULT_RUNTIME_PROFILE


def resume_token_from_reason(reason: str | None) -> str | None:
    """Return a valid v1 resume token without accepting reason-envelope injection."""
    for segment in (reason or "").split("|"):
        if segment.startswith("hh-task:"):
            break
        if not segment.startswith("hh-resume:"):
            continue
        parts = segment.split(":", 2)
        if len(parts) != 3 or parts[1] != f"v{RUNTIME_VERSION}":
            return None
        return parts[2] if _RESUME_TOKEN.fullmatch(parts[2]) else None
    return None


def session_budget(agent: dict, metadata: dict | None) -> RuntimeBudget | None:
    """Resolve trusted local session metadata; ordinary chat sessions return None."""
    raw = (metadata or {}).get(RUNTIME_METADATA_KEY)
    if not isinstance(raw, dict) or raw.get("version") != RUNTIME_VERSION:
        return None
    return effective_budget(agent, raw.get("profile"))
