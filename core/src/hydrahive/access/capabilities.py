"""Katalog der prüfbaren Funktionen (docs/specs/access-groups.md §5, §8).

Nur was hier steht, wird geprüft. Nicht deklarierte Funktionen gelten als für
alle freigegeben (Spec §7 Regel 3), damit Module ohne Angaben nicht brechen.
Der Katalog lebt im Speicher und wird beim Start aus Core-Liste + Manifesten
aufgebaut. ``CATALOG`` ist die laufende Instanz.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from hydrahive.modules.manifest import ModuleManifest


@dataclass(frozen=True)
class Capability:
    id: str
    label: str
    default: str            # "everyone" | "admin_only"
    module_id: str = ""     # leer = Core
    tools: tuple[str, ...] = ()


CORE_CAPABILITIES: tuple[Capability, ...] = (
    Capability("core.vms", "Virtuelle Maschinen", "admin_only"),
    Capability("core.containers", "Container", "admin_only"),
    Capability("core.federation", "Föderation (Workstations fernsteuern)", "admin_only"),
)


@dataclass
class Catalog:
    _caps: dict[str, Capability] = field(default_factory=dict)
    _tool_map: dict[tuple[str, str], str] = field(default_factory=dict)

    @classmethod
    def with_core(cls) -> "Catalog":
        cat = cls()
        for cap in CORE_CAPABILITIES:
            cat._caps[cap.id] = cap
        return cat

    def register_module(self, manifest: ModuleManifest) -> None:
        self.unregister_module(manifest.id)
        if not manifest.capabilities:
            return
        base_id = f"module.{manifest.id}"
        specs = list(manifest.capabilities)
        if not any(s.id == base_id for s in specs):
            self._caps[base_id] = Capability(base_id, manifest.name, "everyone", manifest.id)
        for s in specs:
            self._caps[s.id] = Capability(s.id, s.label, s.default, manifest.id, s.tools)
            for tool in s.tools:
                self._tool_map[(manifest.id, tool)] = s.id

    def unregister_module(self, module_id: str) -> None:
        for cap_id in [c.id for c in self._caps.values() if c.module_id == module_id and module_id]:
            del self._caps[cap_id]
        for key in [k for k in self._tool_map if k[0] == module_id]:
            del self._tool_map[key]

    def is_declared(self, cap_id: str) -> bool:
        return cap_id in self._caps

    def get(self, cap_id: str) -> Capability:
        return self._caps[cap_id]

    def all(self) -> list[Capability]:
        """Core zuerst, dann je Modul die Grundfreigabe vor den feineren Funktionen."""
        def key(c: Capability) -> tuple:
            return (c.module_id != "", c.module_id, not c.id.startswith("module."), c.id)
        return sorted(self._caps.values(), key=key)

    def capability_for_tool(self, tool_name: str, *, module_id: str) -> str | None:
        """Funktion, die ein Werkzeug freischaltet. None = Werkzeug wird nicht geprüft."""
        if not module_id:
            return None
        mapped = self._tool_map.get((module_id, tool_name))
        if mapped:
            return mapped
        base = f"module.{module_id}"
        return base if base in self._caps else None


CATALOG = Catalog.with_core()


def catalog() -> Catalog:
    """Die laufende Instanz. Immer darüber zugreifen, nie per ``from … import CATALOG``,
    damit Laden von Modulen und Tests überall dieselbe Instanz sehen."""
    return CATALOG
