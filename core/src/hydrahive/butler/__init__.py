"""Butler — visueller Flow-Builder für Trigger → Condition → Action-Regeln.

Public API:
- `models` — Flow / Node / Edge / TriggerEvent (Pydantic)
- `persistence` — Load/Save-Layer pro Owner unter $HH_CONFIG_DIR/butler/<owner>/
- `registry` — Trigger-, Condition-, Action-Registries (Plugin-Pattern)
"""
from __future__ import annotations
