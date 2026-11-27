import type { AreaCatalog, AreaInfo } from "./areasApi"

/** Ein Bereich ist „an“, wenn alle seine vergebbaren Tools im Pool stehen (nie vergebbare zählen nicht). */
export function areaIsOn(area: AreaInfo, items: Set<string>, never: Set<string>): boolean {
  const own = area.tools.filter((t) => !never.has(t))
  return own.length > 0 && own.every((t) => items.has(t))
}

/**
 * Neue Pool-Liste aus den eingeschalteten Bereichen. Gespeichert werden TOOL-NAMEN, nie Bereichs-IDs oder `kategorie:x`.
 * Einträge, die zu keinem Bereich gehören (Kategorien, noch nicht zugeordnete Tools), bleiben unverändert erhalten.
 */
export function applyAreas(items: string[], areas: AreaInfo[], on: Set<string>, never: Set<string>): string[] {
  const known = new Set(areas.flatMap((a) => a.tools))
  const kept = items.filter((i) => !known.has(i))
  const added = areas.filter((a) => on.has(a.id)).flatMap((a) => a.tools.filter((t) => !never.has(t)))
  return [...new Set([...kept, ...added])]
}

/** Ein Schalter wurde umgelegt: die neue Pool-Liste (Tool-Namen). Nie vergebbare Bereiche lassen sich nicht einschalten. */
export function toggleArea(items: string[], catalog: AreaCatalog, areaId: string, on: boolean): string[] {
  const now = new Set(items)
  const current = new Set(catalog.areas.filter((a) => areaIsOn(a, now, catalog.never)).map((a) => a.id))
  if (on && !catalog.neverAreas.has(areaId)) current.add(areaId)
  else if (!on) current.delete(areaId)
  return applyAreas(items, catalog.areas, current, catalog.never)
}
