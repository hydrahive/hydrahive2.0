"""Läuft HydraHive auf einem Mac? (Plan docs/plans/mac-containers.md)

Auf dem Mac liegt Incus in einer Linux-VM (Colima). Die wenigen Stellen, die dort anders arbeiten müssen
(Netzmodi, Portfreigaben), fragen genau hier – der Linux-Weg bleibt unverändert.
"""
from __future__ import annotations

import sys


def is_mac() -> bool:
    return sys.platform == "darwin"
