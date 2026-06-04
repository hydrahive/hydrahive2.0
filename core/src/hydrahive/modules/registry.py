from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from hydrahive.modules.manifest import ModuleManifest
from hydrahive.modules.context import ModuleContext


@dataclass
class LoadedModule:
    name: str
    manifest: ModuleManifest | None
    path: Path
    ctx: ModuleContext | None = None
    loaded: bool = False
    error: str | None = None


REGISTRY: dict[str, LoadedModule] = {}
