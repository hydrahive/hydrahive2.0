export interface InstalledTheme {
  id: string
  name?: string
  loaded: boolean
  error: string | null
  version: string | null
  protected?: boolean
}

export interface AvailableTheme {
  id: string
  name?: string
  path?: string
}

export interface ThemesIndex {
  installed: InstalledTheme[]
  available: AvailableTheme[]
}
