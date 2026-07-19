-- 037: VM execution backend; legacy VMs continue to use local QEMU.
ALTER TABLE vms ADD COLUMN runtime TEXT NOT NULL DEFAULT 'qemu' CHECK (runtime IN ('qemu', 'incus'));
