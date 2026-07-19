"""Compute-cluster PKI paths."""

from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path


class _ComputeMixin:
    @cached_property
    def compute_pki_dir(self) -> Path:
        return Path(os.environ.get("HH_COMPUTE_PKI_DIR", str(self.config_dir / "compute-pki")))

    @cached_property
    def compute_ca_key_path(self) -> Path:
        return self.compute_pki_dir / "ca-key.pem"

    @cached_property
    def compute_ca_cert_path(self) -> Path:
        return self.compute_pki_dir / "ca-cert.pem"
