"""Plugin-Manifest: plugin.yaml parsen + minimal validieren.

Im MVP ist das ein schlanker Strict-Parser. Spätere Feature-Erweiterungen
(Permissions enforcement, dependencies) hängen sich hier an.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ManifestError(ValueError):
    """plugin.yaml ist kaputt oder unvollständig."""


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    entry: str = "__init__"
    requires_core: str | None = None
    author: str | None = None
    permissions: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        if not isinstance(data, dict):
            raise ManifestError("plugin.yaml: Top-Level muss ein Mapping sein")
        for required in ("name", "version", "description"):
            if not data.get(required):
                raise ManifestError(f"plugin.yaml: Feld '{required}' fehlt")
        name = str(data["name"]).strip()
        if not name or "/" in name or name.startswith("."):
            raise ManifestError(f"plugin.yaml: ungültiger name '{name}'")
        permissions = data.get("permissions") or []
        if not isinstance(permissions, list):
            raise ManifestError("plugin.yaml: 'permissions' muss eine Liste sein")
        return cls(
            name=name,
            version=str(data["version"]),
            description=str(data["description"]),
            entry=str(data.get("entry") or "__init__"),
            requires_core=data.get("requires_core"),
            author=data.get("author"),
            permissions=[str(p) for p in permissions],
        )

    @classmethod
    def from_file(cls, path: Path) -> "PluginManifest":
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise ManifestError(f"plugin.yaml ungültiges YAML: {e}") from e
        return cls.from_dict(data or {})
