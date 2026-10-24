// Reine Logik der Bereiche (docs/specs/startdesktop.md): verteilen, Bereich zu Pfad, Einstieg, Menü-Reihenfolge.
import type { NavItem } from "@/shared/nav-config"
import { AREAS, HIDDEN_PATHS, OTHER_AREA, type Area } from "./areas"

export interface FilledArea {
  area: Area
  items: NavItem[]
}

const startsPath = (pathname: string, base: string) => pathname === base || pathname.startsWith(`${base}/`)

/**
 * Verteilt die sichtbaren Apps auf die Bereiche.
 * - Modul-Angabe `area` hat Vorrang vor der Tabelle (unbekannte Angabe → Tabelle).
 * - Reihenfolge im Bereich: erst Tabellen-Reihenfolge, dann per `area` Zugeordnetes in Eingangsreihenfolge.
 * - Leere Bereiche entfallen; Admin-Bereiche für Nicht-Admins auch – deren Apps landen in „Weitere“.
 */
export function fillAreas(visible: NavItem[], isAdmin: boolean): FilledArea[] {
  const known = new Map(AREAS.map((a) => [a.id, a]))
  const byPath = new Map<string, NavItem>()
  for (const item of visible) if (!HIDDEN_PATHS.includes(item.path) && !byPath.has(item.path)) byPath.set(item.path, item)

  const target = new Map<string, string>()
  for (const item of byPath.values()) {
    const own = item.area && known.has(item.area) ? item.area : null
    const table = AREAS.find((a) => a.paths.includes(item.path))?.id ?? null
    const id = own ?? table
    if (id && (isAdmin || !known.get(id)!.adminOnly)) target.set(item.path, id)
  }

  const out: FilledArea[] = []
  for (const area of AREAS) {
    const fromTable = area.paths.filter((p) => target.get(p) === area.id).map((p) => byPath.get(p)!)
    const extra = [...byPath.values()].filter((i) => target.get(i.path) === area.id && !area.paths.includes(i.path))
    const items = [...fromTable, ...extra]
    if (items.length > 0) out.push({ area, items })
  }
  const rest = [...byPath.values()].filter((i) => !target.has(i.path))
  if (rest.length > 0) out.push({ area: OTHER_AREA, items: rest })
  return out
}

/** Bereich und App zu einem Pfad; längster passender App-Pfad gewinnt. */
export function areaForPath(areas: FilledArea[], pathname: string): { area: FilledArea; item: NavItem } | null {
  let best: { area: FilledArea; item: NavItem } | null = null
  for (const area of areas) for (const item of area.items) {
    if (startsPath(pathname, item.path) && (!best || item.path.length > best.item.path.length)) best = { area, item }
  }
  return best
}

/** Wohin eine Bereichs-Kachel führt: zuletzt benutzter Pfad, wenn er noch zu einer App des Bereichs gehört. */
export function entryPath(area: FilledArea, last: Record<string, string>): string {
  const remembered = last[area.area.id]
  if (remembered && area.items.some((i) => startsPath(remembered, i.path))) return remembered
  return area.items[0].path
}

/** Bereiche für den Kasten: aktueller zuerst; mit Suche nur passende Apps, leere Bereiche fallen weg. */
export function orderForMenu(areas: FilledArea[], activeId: string | null, query = "", label?: (i: NavItem) => string): FilledArea[] {
  const ordered = [...areas].sort((a, b) => Number(b.area.id === activeId) - Number(a.area.id === activeId))
  const needle = query.trim().toLowerCase()
  if (!needle || !label) return ordered
  return ordered
    .map((a) => ({ ...a, items: a.items.filter((i) => label(i).toLowerCase().includes(needle)) }))
    .filter((a) => a.items.length > 0)
}
