"""Freigaben und Gruppen (docs/specs/access-groups.md).

Etappe 1: Gruppen, Funktions-Freigaben, Prüfung und Audit.
Öffentliche Einstiegspunkte liegen in den Untermodulen:
  - store:        Gruppen, Mitglieder, Audit
  - grants:       Funktions-Freigaben
  - capabilities: Katalog der prüfbaren Funktionen
  - check:        Entscheidung „darf dieser Nutzer diese Funktion?“
"""
