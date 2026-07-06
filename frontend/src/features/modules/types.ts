export interface InstalledModule {
  id: string
  loaded: boolean
  error: string | null
  version: string | null
  available_version?: string | null
  update_available?: boolean
}

export interface AvailableModule {
  id: string
  name?: string
  path?: string
}

export interface ModulesIndex {
  installed: InstalledModule[]
  available: AvailableModule[]
}
