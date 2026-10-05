export type DesiredState = "running" | "stopped"
export type ActualState = "created" | "starting" | "running" | "stopping" | "stopped" | "error"
export type NetworkMode = "bridged" | "isolated" | "nat"

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
  node_id: string
  generation: number
  ipv4?: string | null
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
  node_id?: string
}

// Portfreigaben für NAT-Container (docs/specs/container-nat-ports.md)
export type PortScope = "public" | "tailnet" | "off"
export type PortProtocol = "tcp" | "udp"

export interface PortRule {
  id: string
  container_id: string
  protocol: PortProtocol
  host_port_start: number
  host_port_end: number
  container_port_start: number
  scope: PortScope
  label: string
  created_at: string
  applied_at: string | null
  last_error: string | null
}

export interface PortList {
  ipv4: string | null
  network_mode: NetworkMode
  ports: PortRule[]
}

export interface PortCreateInput {
  protocol: PortProtocol
  host_port_start: number
  host_port_end?: number | null
  container_port_start?: number | null
  scope: PortScope
  label?: string
}

export interface NetworkModes {
  bridged: boolean
  nat: boolean
  isolated: boolean
  default: NetworkMode
}
