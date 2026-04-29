export type DesiredState = "running" | "stopped"
export type ActualState = "created" | "starting" | "running" | "stopping" | "stopped" | "error"
export type NetworkMode = "bridged" | "isolated"

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

export interface VMCreateInput {
  name: string
  description?: string | null
  cpu: number
  ram_mb: number
  disk_gb: number
  iso_filename?: string | null
  network_mode: NetworkMode
}
