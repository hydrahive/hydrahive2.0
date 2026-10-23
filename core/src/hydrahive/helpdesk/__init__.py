"""Hilfe-Assistent: Fenster unten rechts im Cockpit (docs/plans/help-assistant.md).

Bewusst ohne Importe: die Werkzeuge (tools/help_*.py) brauchen nur helpdesk._manual. Würde dieses Paket beim
Laden helpdesk._agent ziehen (→ agents → tools), entstünde ein Import-Kreis (tools → help_search → helpdesk → tools).
Den Agenten über `from hydrahive.helpdesk._agent import get_or_create_help_agent` holen.
"""
