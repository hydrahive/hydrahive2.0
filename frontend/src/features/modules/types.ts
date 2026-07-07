/** Ein Modul in der vereinheitlichten Liste (installiert oder verfügbar). */
export interface ModuleEntry {
  id: string
  name: string
  description: string
  installed: boolean
  loaded: boolean
  error: string | null
  /** Installierte Version (null wenn nicht installiert). */
  version: string | null
  /** Version im Hub (null wenn nicht ermittelbar). */
  available_version: string | null
  update_available: boolean
}

export interface ModulesIndex {
  modules: ModuleEntry[]
}
