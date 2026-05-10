export type DesiredState = "running" | "stopped"
export type ActualState = "created" | "starting" | "running" | "stopping" | "stopped" | "error"
export type NetworkMode = "bridged" | "isolated"
export type DiskInterface = "virtio" | "sata" | "ide"
export type MachineType = "q35" | "pc"
export type NetworkDevice = "virtio-net-pci" | "e1000"

export interface VM {
  vm_id: string
  owner: string
  name: string
  description: string | null
  cpu: number
  ram_mb: number
  disk_gb: number
  iso_filename: string | null
  network_mode: NetworkMode
  qcow2_path: string
  disk_interface: DiskInterface
  machine_type: MachineType
  network_device: NetworkDevice
  desired_state: DesiredState
  actual_state: ActualState
  pid: number | null
  vnc_port: number | null
  vnc_token: string | null
  last_error_code: string | null
  last_error_params: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface ISO {
  filename: string
  size_bytes: number
  sha256: string
  uploaded_at: string
}

export interface Snapshot {
  snapshot_id: string
  vm_id: string
  name: string
  description: string | null
  size_bytes: number | null
  created_at: string
}

export interface ImportJob {
  job_id: string
  owner: string
  source_path: string
  target_qcow2: string
  status: "queued" | "running" | "done" | "failed"
  progress_pct: number
  bytes_done: number
  bytes_total: number
  error_code: string | null
  created_at: string
  finished_at: string | null
}

export interface VMCreateInput {
  name: string
  description?: string | null
  cpu: number
  ram_mb: number
  disk_gb: number
  iso_filename?: string | null
  network_mode: NetworkMode
  disk_interface?: DiskInterface
  machine_type?: MachineType
  network_device?: NetworkDevice
}
