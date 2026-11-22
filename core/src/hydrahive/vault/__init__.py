"""Vault: PIN-Sperre für sensible Bereiche der Oberfläche (docs/specs/vault.md).

Die PIN schützt das Ansehen in der Oberfläche. Vault-Werkzeuge der Agenten liefern nur bei entsperrtem Vault
Daten (agent_gate.py, unlocks.py; Ziel vault-agenten). API-Keys und Geräte-Routen sind nicht gesperrt.
"""
