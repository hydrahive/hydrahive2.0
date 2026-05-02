from __future__ import annotations

from pydantic import BaseModel, Field

from hydrahive.vms.models import (
    MAX_CPU, MAX_DISK_GB, MAX_RAM_MB, MIN_CPU, MIN_DISK_GB, MIN_RAM_MB,
)


class VMCreate(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    description: str | None = Field(default=None, max_length=500)
    cpu: int = Field(ge=MIN_CPU, le=MAX_CPU)
    ram_mb: int = Field(ge=MIN_RAM_MB, le=MAX_RAM_MB)
    disk_gb: int = Field(ge=MIN_DISK_GB, le=MAX_DISK_GB)
    iso_filename: str | None = None
    network_mode: str = "bridged"
    import_job_id: str | None = None


class VMUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=32)
    description: str | None = Field(default=None, max_length=500)
    cpu: int | None = Field(default=None, ge=MIN_CPU, le=MAX_CPU)
    ram_mb: int | None = Field(default=None, ge=MIN_RAM_MB, le=MAX_RAM_MB)
    disk_gb: int | None = Field(default=None, ge=MIN_DISK_GB, le=MAX_DISK_GB)
    iso_filename: str | None = None
    clear_iso: bool = False
