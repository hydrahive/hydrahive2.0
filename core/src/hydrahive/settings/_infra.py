"""Infra-Mixins: Samba, VMs, Extensions, Butler."""
from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path


class _SambaMixin:
    @cached_property
    def samba_includes_dir(self) -> Path:
        """Verzeichnis in dem die per-Projekt-Smb-Configs liegen.
        smb.conf hat ein `include = .../*.conf`."""
        return Path(os.environ.get("HH_SAMBA_INCLUDES_DIR", "/etc/samba/hh-projects.d"))

    @cached_property
    def samba_user(self) -> str:
        """Gemeinsamer Samba-User für Projekt-Shares. Später (Issue: Per-User-
        Auth) wird das durch Mapping auf HH-User abgelöst."""
        return os.environ.get("HH_SAMBA_USER", "hh").strip() or "hh"

    @cached_property
    def samba_password_file(self) -> Path:
        return Path(os.environ.get("HH_SAMBA_PASSWORD_FILE",
                                    str(self.config_dir / "samba.password")))


class _VmsMixin:
    @cached_property
    def vms_dir(self) -> Path:
        return self.data_dir / "vms"

    @cached_property
    def vms_isos_dir(self) -> Path:
        return self.vms_dir / "isos"

    @cached_property
    def vms_disks_dir(self) -> Path:
        return self.vms_dir / "disks"

    @cached_property
    def vms_pids_dir(self) -> Path:
        return self.vms_dir / "pids"

    @cached_property
    def vms_logs_dir(self) -> Path:
        return self.vms_dir / "logs"

    @cached_property
    def vms_vnc_tokens_dir(self) -> Path:
        return self.vms_dir / "vnc-tokens"

    @cached_property
    def vms_bridge(self) -> str:
        return os.environ.get("HH_VMS_BRIDGE", "br0")


class _ExtensionsMixin:
    @cached_property
    def extensions_manifests_dir(self) -> Path:
        return self.base_dir / "extensions" / "manifests"

    @cached_property
    def extensions_install_dir(self) -> Path:
        return self.base_dir / "extensions" / "install"

    @cached_property
    def extensions_uninstall_dir(self) -> Path:
        return self.base_dir / "extensions" / "uninstall"


class _WebminMixin:
    @cached_property
    def webmin_url(self) -> str:
        """Webmin-URL (z.B. https://192.168.3.22:10000). Leer ⇒ Webmin-Tools nicht registriert."""
        return os.environ.get("HH_WEBMIN_URL", "").strip().rstrip("/")

    @cached_property
    def webmin_credential(self) -> str:
        """Credential-Profilname für Webmin Basic Auth (default: 'webmin')."""
        return os.environ.get("HH_WEBMIN_CREDENTIAL", "webmin").strip()


class _ButlerMixin:
    @cached_property
    def butler_dir(self) -> Path:
        return self.config_dir / "butler"

    @cached_property
    def butler_secrets_file(self) -> Path:
        return self.config_dir / "butler_hook_secrets.json"
