"""Shared validation and normalization for Ollama model management."""
from __future__ import annotations

import re

_FAMILY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}(?::[a-zA-Z0-9][a-zA-Z0-9._-]{0,127})?$")


def validate_family_name(value: str) -> str:
    name = value.strip()
    if not _FAMILY_RE.fullmatch(name):
        raise ValueError("invalid_ollama_family")
    return name


def normalize_model_name(value: str) -> str:
    name = value.strip()
    if name.startswith("ollama/"):
        name = name[7:]
    if not _MODEL_RE.fullmatch(name):
        raise ValueError("invalid_ollama_model")
    return name
