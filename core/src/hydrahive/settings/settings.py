"""Settings — Single source of truth für alle Pfade und Runtime-Config.

Werte kommen aus Env-Variablen mit sensiblen Defaults. Niemals Pfade
hardcoden — überall via `from hydrahive.settings import settings`
nutzen.

Properties sind in Mixins gruppiert:
- `_paths.py`: Verzeichnisse, Configs, Logs + ensure_dirs()
- `_services.py`: Server, JWT, AgentLink, Communication
- `_infra.py`: Samba, VMs, Extensions, Butler
"""

from __future__ import annotations

from hydrahive.settings._compute import _ComputeMixin
from hydrahive.settings._infra import (
    _ButlerMixin,
    _ExtensionsMixin,
    _SambaMixin,
    _VmsMixin,
    _WebminMixin,
)
from hydrahive.settings._mail import _MailMixin
from hydrahive.settings._teamchat import _TeamchatMixin
from hydrahive.settings._paths import _PathsMixin
from hydrahive.settings._services import (
    _AgentLinkMixin,
    _CommunicationMixin,
    _ServerMixin,
)


class Settings(
    _PathsMixin,
    _ServerMixin,
    _AgentLinkMixin,
    _CommunicationMixin,
    _MailMixin,
    _TeamchatMixin,
    _ComputeMixin,
    _SambaMixin,
    _VmsMixin,
    _ExtensionsMixin,
    _WebminMixin,
    _ButlerMixin,
):
    """Aggregiert alle Settings-Mixins zu einem Singleton."""


# Module-level singleton — überall importieren
settings = Settings()
