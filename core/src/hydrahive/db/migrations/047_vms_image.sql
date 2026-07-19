-- 047: Source image reference for image-based (remote Incus) VMs.
-- Local QEMU VMs keep NULL; only remote image VMs record their launch image.
ALTER TABLE vms ADD COLUMN image TEXT;
