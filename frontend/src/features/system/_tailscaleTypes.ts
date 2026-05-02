export interface TailscalePeer {
  hostname: string
  dns_name: string
  ip?: string
  online: boolean
  os?: string
  exit_node: boolean
  exit_node_option: boolean
  last_seen: string
}

export interface TailscaleStatus {
  installed: boolean
  connected: boolean
  backend_state?: string
  ip?: string
  hostname?: string
  dns_name?: string
  tailnet?: string
  version?: string
  magic_dns?: boolean
  auth_url?: string
  peers?: TailscalePeer[]
  exit_node_active?: string
  error?: string
}
