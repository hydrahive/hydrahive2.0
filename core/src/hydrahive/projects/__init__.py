"""Projects-Layer: zweite Ebene der 3-Ebenen-Architektur.

Ein Projekt = isolierter Workspace + gekoppelter Project-Agent + Members.
Auto-erstellt seinen Project-Agent beim Anlegen, cascade-deleted ihn beim Löschen.
"""

from hydrahive.projects import config
from hydrahive.projects._paths import workspace_path
from hydrahive.projects._validation import ProjectValidationError

__all__ = ["config", "workspace_path", "ProjectValidationError"]
