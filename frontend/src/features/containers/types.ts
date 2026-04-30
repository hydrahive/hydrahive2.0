export type DesiredState = "running" | "stopped"
export type ActualState = "created" | "starting" | "running" | "stopping" | "stopped" | "error"
export type NetworkMode = "bridged" | "isolated"

export interface Container {
  container_id: string
  owner: string
  name: string
  description: string | null
  image: string
  cpu: number | null
  ram_mb: number | null
  network_mode: NetworkMode
  desired_state: DesiredState
  actual_state: ActualState
  last_error_code: string | null
  last_error_params: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface ContainerInfo {
  alive: boolean
  status?: string
  ipv4?: string | null
  cpu_usage_ns?: number
  memory_bytes?: number
  memory_peak_bytes?: number
}

export interface ContainerCreateInput {
  name: string
  description?: string | null
  image: string
  cpu?: number | null
  ram_mb?: number | null
  network_mode: NetworkMode
}
