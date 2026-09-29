// Pfad → Funktion und „darf der Nutzer das sehen?“ (access-groups §9, Menü + Seiten-Sperre).
// Nur Oberfläche: Die Schnittstellen sperren ohnehin mit 403.
import type { MyAccess } from "./types"

const CORE_PATHS: Record<string, string> = {
  "/vms": "core.vms",
  "/containers": "core.containers",
  "/federation": "core.federation",
}

function matches(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`)
}

/** modulePaths: Nav-Pfad eines Moduls → Modul-ID (aus der Modul-Nav). */
export function capabilityForPath(path: string, modulePaths: Record<string, string> = {}): string | null {
  for (const [prefix, cap] of Object.entries(CORE_PATHS)) if (matches(path, prefix)) return cap
  for (const [prefix, mid] of Object.entries(modulePaths)) if (matches(path, prefix)) return `module.${mid}`
  return null
}

export function pathAllowed(path: string, access: MyAccess | null, modulePaths: Record<string, string> = {}): boolean {
  if (!access || access.admin) return true
  const cap = capabilityForPath(path, modulePaths)
  if (!cap || !access.declared.includes(cap)) return true
  return Boolean(access.capabilities[cap])
}
