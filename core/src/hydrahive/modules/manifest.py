from __future__ import annotations
import json, re
from dataclasses import dataclass
from pathlib import Path

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class ManifestError(Exception): ...


@dataclass(frozen=True)
class ModuleManifest:
    id: str
    name: str
    version: str
    icon: str = "Boxes"
    nav_group: str = "working"
    permissions: tuple[str, ...] = ()
    has_service: bool = False
    min_core_version: str = "2.0.0"

    @classmethod
    def load(cls, path: Path) -> "ModuleManifest":
        try:
            d = json.loads(Path(path).read_text())
        except (OSError, json.JSONDecodeError) as e:
            raise ManifestError(f"manifest.json nicht lesbar: {e}") from e
        for key in ("id", "name", "version"):
            if not d.get(key):
                raise ManifestError(f"manifest.json: Pflichtfeld '{key}' fehlt")
        if not _ID_RE.match(d["id"]):
            raise ManifestError(f"manifest.json: ungültige id {d['id']!r} (nur a-z0-9-)")
        return cls(
            id=d["id"], name=d["name"], version=str(d["version"]),
            icon=d.get("icon", "Boxes"), nav_group=d.get("nav_group", "working"),
            permissions=tuple(d.get("permissions", [])),
            has_service=bool(d.get("has_service", False)),
            min_core_version=d.get("min_core_version", "2.0.0"),
        )
