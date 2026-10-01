"""Herkunft eines Laufs — entscheidet über Hintergrund-Modus und Vertrauen.

Default ist `other`: synchron, vertrauenswürdig wie bisher. Nur zwei Wege
setzen eine Herkunft (docs/specs/agent-background-delegation.md):

- `chat`: Der Nutzer hat im Chat geschrieben (start_run_task). ask_agent darf
  interne Spezialisten im Hintergrund beauftragen.
- `delegation`: Zustell-Lauf mit Spezialisten-Ergebnissen. Der Eingabetext stammt
  NICHT vom Nutzer, deshalb ist der Lauf nicht vertrauenswürdig: Tools, die eine
  Nutzer-Absicht prüfen (current_user_input), sehen hier None.
"""
from __future__ import annotations

from dataclasses import dataclass

MAX_CHAIN_DEPTH = 3


@dataclass(frozen=True, slots=True)
class RunOrigin:
    kind: str = "other"          # chat | delegation | other
    depth: int = 0               # Kettentiefe automatischer Folgeläufe

    @property
    def background_allowed(self) -> bool:
        return self.kind in ("chat", "delegation")

    @property
    def trusted_user_input(self) -> bool:
        return self.kind != "delegation"

    def as_metadata(self) -> dict:
        return {"origin": self.kind, "origin_depth": self.depth}


CHAT = RunOrigin("chat", 0)
OTHER = RunOrigin()


def delegation(depth: int) -> RunOrigin:
    return RunOrigin("delegation", max(1, depth))
