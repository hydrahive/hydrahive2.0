-- 008: Per-VM Disk-Interface (virtio/sata/ide).
--
-- Hintergrund: importierte qcow2-Images aus VirtualBox/HydraHive1/etc.
-- haben oft keine virtio-Treiber im Bootloader. Mit dem bisherigen
-- harten Default `virtio` schlug der Boot fehl ("no bootable device").
--
-- Default `virtio` für neue VMs (schnellste Performance unter KVM).
-- User wählt im Create-Dialog `sata` für importierte Images.

ALTER TABLE vms ADD COLUMN disk_interface TEXT NOT NULL DEFAULT 'virtio';
