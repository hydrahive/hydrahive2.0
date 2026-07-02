"""ThemeManifest — liest und validiert theme.json eines Theme-Pakets.

Ein Theme ist reines Frontend: Layout-Wahl + CSS-Variablen. Kein Service,
keine DB, keine Agent-Tools (anders als ein Modul-Manifest).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class ManifestError(Exception): ...


@dataclass(frozen=True)
class ThemeManifest:
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    layout: str = "topnav"
    variables: dict[str, str] = field(default_factory=dict)
    min_core_version: str = "2.0.0"

    @classmethod
    def load(cls, path: Path) -> "ThemeManifest":
        try:
            d = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise ManifestError(f"theme.json nicht lesbar: {e}") from e
        for key in ("id", "name", "version"):
            if not d.get(key):
                raise ManifestError(f"theme.json: Pflichtfeld '{key}' fehlt")
        if not _ID_RE.match(d["id"]):
            raise ManifestError(f"theme.json: ungültige id {d['id']!r} (nur a-z0-9-)")
        variables = d.get("variables", {})
        if not isinstance(variables, dict):
            raise ManifestError("theme.json: 'variables' muss ein Objekt sein")
        return cls(
            id=d["id"],
            name=d["name"],
            version=str(d["version"]),
            description=d.get("description", ""),
            author=d.get("author", ""),
            layout=d.get("layout", "topnav"),
            variables={str(k): str(v) for k, v in variables.items()},
            min_core_version=d.get("min_core_version", "2.0.0"),
        )
