"""Validation primitives for the fixed Incus operation allowlist."""

from __future__ import annotations

import re

NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9-]{0,62}$")
IMAGE_RE = re.compile(r"^(?:[a-zA-Z0-9][a-zA-Z0-9-]*:)?[a-zA-Z0-9][a-zA-Z0-9._/-]*$")
LIFECYCLE_FIELDS = {"name"}
CREATE_FIELDS = {"name", "image", "network_mode", "cpu", "ram_mb"}


class IncusJobError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def name(value: object) -> str:
    if not isinstance(value, str) or NAME_RE.fullmatch(value) is None:
        raise IncusJobError("container_name_invalid")
    return value


def image(value: object) -> str:
    if not isinstance(value, str) or IMAGE_RE.fullmatch(value) is None:
        raise IncusJobError("container_image_invalid")
    return value


def optional_int(value: object, minimum: int, maximum: int, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise IncusJobError(f"container_{field}_invalid")
    return value
