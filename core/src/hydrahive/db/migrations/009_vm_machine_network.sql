-- 009: Per-VM machine_type + network_device.
--
-- Hintergrund: HH2 hardcoded q35 + virtio-net-pci. Das bricht FreeBSD-
-- ZFS-Boot ("cannot read MOS") und Network-Connectivity bei VMs aus
-- VirtualBox/VMware ohne virtio-Treiber. HH1 hatte beide Switches mit
-- begründeten Defaults — siehe vm_manager.py:459 Kommentar.
--
-- Default 'q35' / 'virtio-net-pci' für neue VMs (modern, schnell).
-- User wählt im Create-Dialog 'pc' / 'e1000' für importierte Images.

ALTER TABLE vms ADD COLUMN machine_type TEXT NOT NULL DEFAULT 'q35';
ALTER TABLE vms ADD COLUMN network_device TEXT NOT NULL DEFAULT 'virtio-net-pci';
