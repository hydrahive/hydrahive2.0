-- 028: Passthrough-Disks für VMs — physische Block-Devices direkt in QEMU.
--
-- Nur Admins dürfen Passthrough-Disks verwalten (API-Schicht erzwingt das).
-- device_path ist der abs. Pfad zum Block-Device auf dem Host (/dev/sdX etc.).

CREATE TABLE vm_passthrough_disks (
    passthrough_id  TEXT PRIMARY KEY,
    vm_id           TEXT NOT NULL REFERENCES vms(vm_id) ON DELETE CASCADE,
    device_path     TEXT NOT NULL,
    label           TEXT,
    added_at        TEXT NOT NULL,
    UNIQUE(vm_id, device_path)
);

CREATE INDEX idx_passthrough_vm ON vm_passthrough_disks(vm_id);
