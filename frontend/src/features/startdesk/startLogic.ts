// VORSCHAU Startdesktop: Apps (aus nav-config inkl. Module) auf die Kachel-Gruppen verteilen.
import { Settings } from "lucide-react"
import type { NavItem } from "@/shared/nav-config"
import { HIDDEN_PATHS, OTHER_GROUP, START_GROUPS, type StartGroup } from "./groups"

/** Seiten, die keine Menüeinträge sind, aber in eine Gruppe gehören. */
export const EXTRA_ITEMS: NavItem[] = [
  { path: "/settings", icon: Settings, labelKey: "settings_hub", group: "settings", roles: ["admin"] },
]

export interface FilledGroup {
  group: StartGroup
  items: NavItem[]
}

/**
 * Verteilt die sichtbaren Apps auf die Gruppen.
 * - Reihenfolge innerhalb einer Gruppe wie in `paths`.
 * - Apps ohne Gruppe landen in „Weitere“ (neue Module fallen so nicht durch).
 * - Leere Gruppen und Admin-Gruppen für Nicht-Admins entfallen; deren für alle sichtbare Apps landen dann in „Weitere“.
 */
export function fillGroups(visible: NavItem[], isAdmin: boolean): FilledGroup[] {
  const byPath = new Map<string, NavItem>()
  for (const item of visible) if (!HIDDEN_PATHS.includes(item.path)) byPath.set(item.path, item)
  const used = new Set<string>()
  const out: FilledGroup[] = []
  for (const group of START_GROUPS) {
    if (group.adminOnly && !isAdmin) continue
    const items = group.paths.map((p) => byPath.get(p)).filter((i): i is NavItem => Boolean(i))
    items.forEach((i) => used.add(i.path))
    if (items.length > 0) out.push({ group, items })
  }
  const rest = [...byPath.values()].filter((i) => !used.has(i.path))
  if (rest.length > 0) out.push({ group: OTHER_GROUP, items: rest })
  return out
}
