"""PluginContext: was ein Plugin beim on_load() bekommt.

Ein schmales Interface — Plugins sollen nicht direkt am Core schrauben,
sondern über diese Schnittstelle ihre Tools/Hooks anmelden.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from hydrahive.tools.base import Tool


@dataclass
class PluginContext:
    plugin_name: str
    plugin_dir: Path
    logger: logging.Logger
    _tools: list[Tool] = field(default_factory=list)

    def register_tool(self, tool: Tool) -> None:
        """Macht ein Tool im Core sichtbar.

        Der Core hängt automatisch den Namespace `plugin__<plugin-name>__`
        davor — Plugin-Code muss sich darum nicht kümmern.
        """
        if not isinstance(tool, Tool):
            raise TypeError(f"register_tool: erwartet Tool, bekam {type(tool)}")
        for existing in self._tools:
            if existing.name == tool.name:
                raise ValueError(
                    f"Tool '{tool.name}' im Plugin '{self.plugin_name}' "
                    "doppelt registriert"
                )
        self._tools.append(tool)

    @property
    def tools(self) -> list[Tool]:
        return list(self._tools)
