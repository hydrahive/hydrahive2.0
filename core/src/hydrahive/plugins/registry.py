"""Registry geladener Plugins.

Modul-Singleton. Loader füllt sie beim Backend-Start, Tool-Bridge + API
lesen davon. Crash-isoliert: ein gescheitertes Plugin landet mit `error`,
verhindert nicht das Laden anderer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hydrahive.plugins.manifest import PluginManifest
from hydrahive.tools.base import Tool


@dataclass
class LoadedPlugin:
    name: str
    manifest: PluginManifest | None
    module: Any = None
    tools: list[Tool] = field(default_factory=list)
    error: str | None = None

    @property
    def loaded(self) -> bool:
        return self.error is None and self.module is not None


REGISTRY: dict[str, LoadedPlugin] = {}


def reset() -> None:
    """Wird vom Loader vor einem Reload genutzt — und im Test."""
    REGISTRY.clear()


def all_plugins() -> list[LoadedPlugin]:
    return list(REGISTRY.values())


def get(name: str) -> LoadedPlugin | None:
    return REGISTRY.get(name)
