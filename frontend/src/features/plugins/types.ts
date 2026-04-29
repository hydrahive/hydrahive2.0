export interface HubPlugin {
  name: string
  version: string
  description: string
  author?: string
  path?: string
  requires_core?: string
  tags?: string[]
}

export interface HubIndex {
  schema_version: number | null
  updated: string | null
  plugins: HubPlugin[]
}

export interface InstalledPlugin {
  name: string
  version: string | null
  description: string | null
  loaded: boolean
  error: string | null
  tools: string[]
}

export interface InstallResponse {
  name: string
  version: string | null
  restart_recommended: boolean
}
