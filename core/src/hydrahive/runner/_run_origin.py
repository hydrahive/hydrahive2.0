"""Herkunft eines Laufs — entscheidet über Hintergrund-Modus und Vertrauen.

Default ist `other`: synchron, vertrauenswürdig wie bisher. Drei Wege setzen
eine Herkunft (docs/specs/agent-background-delegation.md):

- `chat`: Der Nutzer hat im Chat geschrieben (start_run_task). ask_agent darf
  interne Spezialisten im Hintergrund beauftragen.
- `delegation`: Zustell-Lauf mit Spezialisten-Ergebnissen. Der Eingabetext stammt
  NICHT vom Nutzer, deshalb ist der Lauf nicht vertrauenswürdig: Tools, die eine
  Nutzer-Absicht prüfen (current_user_input), sehen hier None.
- `handoff`: Eingehender AgentLink-Auftrag (handoff_receiver), z. B. ein
  Projekt-Agent, der per ask_agent beauftragt wurde. Der Auftraggeber wartet
  bereits synchron auf uns (ask_agent) — wenn WIR jetzt selbst weitere interne
  Spezialisten per ask_agent beauftragen wollen, muss das im Hintergrund
  laufen können, sonst addieren sich die Timeouts der Kette und der äußerste
  Aufrufer läuft ab, bevor die innersten Spezialisten fertig sind (Befund
  2026-11-19: Projekt-Agent-Timeout nach 1200s, während sein Spezialist drei
  Minuten länger noch aktiv weiterarbeitete). Wie `delegation` NICHT
  vertrauenswürdig: der Auftragstext stammt vom Auftraggeber-Agenten, nicht
  vom Endnutzer.
"""
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class RunOrigin:
    kind: str = "other"          # chat | delegation | handoff | other
    depth: int = 0               # Kettentiefe automatischer Folgeläufe

    @property
    def background_allowed(self) -> bool:
        # Gleiche Liste wie tools/_ask_agent_background.BACKGROUND_ORIGINS (dort
        # entscheidet ask_agent); Import wäre ein Zyklus, ein Test prüft Gleichheit.
        return self.kind in ("chat", "delegation", "handoff")

    @property
    def trusted_user_input(self) -> bool:
        return self.kind not in ("delegation", "handoff")

    def as_metadata(self) -> dict:
        return {"origin": self.kind, "origin_depth": self.depth}


CHAT = RunOrigin("chat", 0)
OTHER = RunOrigin()


def delegation(depth: int) -> RunOrigin:
    return RunOrigin("delegation", max(1, depth))


def handoff(depth: int) -> RunOrigin:
    return RunOrigin("handoff", max(1, depth))
