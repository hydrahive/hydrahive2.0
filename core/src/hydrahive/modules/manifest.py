from __future__ import annotations
import json, re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class ManifestError(Exception): ...


def _persistent_paths(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ManifestError("manifest.json: 'persistent_paths' muss eine Liste sein")
    patterns: list[str] = []
    for pattern in value:
        if not isinstance(pattern, str) or not pattern:
            raise ManifestError("manifest.json: 'persistent_paths' enthält kein gültiges Glob-Pattern")
        parts = pattern.split("/")
        posix_path = PurePosixPath(pattern)
        windows_path = PureWindowsPath(pattern)
        if (
            "\\" in pattern
            or "\x00" in pattern
            or posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or any(part in ("", ".", "..") for part in parts)
        ):
            raise ManifestError(
                f"manifest.json: ungültiges relatives persistent_paths-Pattern {pattern!r}"
            )
        patterns.append(pattern)
    return tuple(patterns)


@dataclass(frozen=True)
class ModuleManifest:
    id: str
    name: str
    version: str
    description: str = ""
    icon: str = "Boxes"
    nav_group: str = "working"
    permissions: tuple[str, ...] = ()
    has_service: bool = False
    default_agent_tools: bool = False
    min_core_version: str = "2.0.0"
    dependencies: tuple[str, ...] = ()
    persistent_paths: tuple[str, ...] = ()

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
            description=str(d.get("description", "")),
            icon=d.get("icon", "Boxes"), nav_group=d.get("nav_group", "working"),
            permissions=tuple(d.get("permissions", [])),
            has_service=bool(d.get("has_service", False)),
            default_agent_tools=bool(d.get("default_agent_tools", False)),
            min_core_version=d.get("min_core_version", "2.0.0"),
            dependencies=tuple(d.get("dependencies", [])),
            persistent_paths=_persistent_paths(d.get("persistent_paths", [])),
        )
