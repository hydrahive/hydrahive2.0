-- 003: VM-Management (QEMU/KVM direkt).
--
-- Per-User-Owner. desired_state = was der User will, actual_state = was der
-- Reconciler zuletzt gemessen hat. last_error_* für i18n im Frontend.

CREATE TABLE vms (
    vm_id            TEXT PRIMARY KEY,
    owner            TEXT NOT NULL,
    name             TEXT NOT NULL,
    description      TEXT,
    cpu              INTEGER NOT NULL,
    ram_mb           INTEGER NOT NULL,
    disk_gb          INTEGER NOT NULL,
    iso_filename     TEXT,
    network_mode     TEXT NOT NULL DEFAULT 'bridged',
    qcow2_path       TEXT NOT NULL,
    desired_state    TEXT NOT NULL DEFAULT 'stopped',
    actual_state     TEXT NOT NULL DEFAULT 'created',
    pid              INTEGER,
    vnc_port         INTEGER,
    vnc_token        TEXT,
    last_error_code  TEXT,
    last_error_params TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX idx_vms_owner ON vms(owner);
CREATE INDEX idx_vms_actual_state ON vms(actual_state);

CREATE TABLE vm_snapshots (
    snapshot_id  TEXT PRIMARY KEY,
    vm_id        TEXT NOT NULL REFERENCES vms(vm_id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    description  TEXT,
    size_bytes   INTEGER,
    created_at   TEXT NOT NULL
);

CREATE INDEX idx_snapshots_vm ON vm_snapshots(vm_id);

CREATE TABLE vm_import_jobs (
    job_id        TEXT PRIMARY KEY,
    owner         TEXT NOT NULL,
    source_path   TEXT NOT NULL,
    target_qcow2  TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'queued',
    progress_pct  INTEGER NOT NULL DEFAULT 0,
    bytes_done    INTEGER NOT NULL DEFAULT 0,
    bytes_total   INTEGER NOT NULL DEFAULT 0,
    error_code    TEXT,
    created_at    TEXT NOT NULL,
    finished_at   TEXT
);

CREATE INDEX idx_import_jobs_owner ON vm_import_jobs(owner);
CREATE INDEX idx_import_jobs_status ON vm_import_jobs(status);
