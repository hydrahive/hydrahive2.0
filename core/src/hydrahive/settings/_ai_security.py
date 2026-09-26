"""Konfiguration für das optionale AI-Security-Modul."""
from __future__ import annotations

import os

from hydrahive.settings.overrides import env_or_override


class _AiSecurityMixin:
    """Nicht-sensitive Runtime-Parameter des AI-Security-Adapters."""

    @property
    def ai_security_aig_url(self) -> str:
        return env_or_override(
            "ai_security_aig_url",
            "HH_AI_SECURITY_AIG_URL",
            "http://127.0.0.1:8088",
        ).strip().rstrip("/")

    @property
    def ai_security_targets(self) -> str:
        return env_or_override(
            "ai_security_targets", "HH_AI_SECURITY_TARGETS", ""
        ).strip()

    @property
    def ai_security_model(self) -> str:
        return env_or_override(
            "ai_security_model", "HH_AI_SECURITY_MODEL", ""
        ).strip()

    @property
    def ai_security_model_token(self) -> str:
        return env_or_override(
            "ai_security_model_token", "HH_AI_SECURITY_MODEL_TOKEN", "ollama"
        ).strip()

    @property
    def ai_security_model_base_url(self) -> str:
        return env_or_override(
            "ai_security_model_base_url",
            "HH_AI_SECURITY_MODEL_BASE_URL",
            "http://127.0.0.1:11434/v1",
        ).strip().rstrip("/")

    @property
    def ai_security_http_timeout(self) -> float:
        raw = env_or_override(
            "ai_security_http_timeout", "HH_AI_SECURITY_HTTP_TIMEOUT", "10"
        ).strip()
        try:
            value = float(raw)
        except ValueError as exc:
            raise RuntimeError("HH_AI_SECURITY_HTTP_TIMEOUT muss numerisch sein") from exc
        if not 0.1 <= value <= 120:
            raise RuntimeError("HH_AI_SECURITY_HTTP_TIMEOUT muss zwischen 0.1 und 120 liegen")
        return value

    @property
    def ai_security_max_result_bytes(self) -> int:
        raw = env_or_override(
            "ai_security_max_result_bytes", "HH_AI_SECURITY_MAX_RESULT_BYTES", "2097152"
        ).strip()
        try:
            value = int(raw)
        except ValueError as exc:
            raise RuntimeError("HH_AI_SECURITY_MAX_RESULT_BYTES muss ganzzahlig sein") from exc
        if not 1024 <= value <= 16 * 1024 * 1024:
            raise RuntimeError(
                "HH_AI_SECURITY_MAX_RESULT_BYTES muss zwischen 1024 und 16777216 liegen"
            )
        return value

    @property
    def ai_security_enabled(self) -> bool:
        return os.environ.get("HH_AI_SECURITY_ENABLED", "1").strip().lower() not in {
            "0", "false", "no", "off"
        }
