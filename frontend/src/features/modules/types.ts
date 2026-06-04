export interface InstalledModule {
  id: string
  loaded: boolean
  error: string | null
  version: string | null
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
