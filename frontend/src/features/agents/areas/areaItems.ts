import type { AreaCatalog, AreaInfo } from "./areasApi"

export type PoolAreaState = "on" | "off" | "partial"

/** Zustand eines Bereichs im Pool: an = alle vergebbaren Tools drin, teilweise = einige, aus = keins (nie vergebbare zählen nicht). */
export function areaState(area: AreaInfo, items: Set<string>, never: Set<string>): PoolAreaState {
  const own = area.tools.filter((t) => !never.has(t))
  const have = own.filter((t) => items.has(t)).length
  if (own.length === 0 || have === 0) return "off"
  return have === own.length ? "on" : "partial"
}

/** Ein Bereich ist „an“, wenn alle seine vergebbaren Tools im Pool stehen. */
export function areaIsOn(area: AreaInfo, items: Set<string>, never: Set<string>): boolean {
  return areaState(area, items, never) === "on"
}

/**
 * Ein Schalter wurde umgelegt: ändert den Pool als DIFFERENZ (Review #795, muss). Einschalten = Pool ∪ (Bereich − nie vergebbar),
 * Ausschalten = Pool − Bereich. Alles andere bleibt unverändert: andere, auch teilweise belegte Bereiche, kategorie:x und
 * Unzugeordnetes. Vorher wurde der Pool aus den „ganz an“-Bereichen neu gebaut – Teilbereiche fielen still weg, und ein
 * Projekt-Pool konnte leer (= keine Einschränkung) werden. Gespeichert werden TOOL-NAMEN, nie Bereichs-IDs.
 */
export function toggleArea(items: string[], catalog: AreaCatalog, areaId: string, on: boolean): string[] {
  const area = catalog.areas.find((a) => a.id === areaId)
  if (!area) return items
  if (on) {
    if (catalog.neverAreas.has(areaId)) return items
    const have = new Set(items)
    return [...items, ...area.tools.filter((t, i) => !catalog.never.has(t) && !have.has(t) && area.tools.indexOf(t) === i)]
  }
  const drop = new Set(area.tools)
  return items.filter((i) => !drop.has(i))
}

/** Würde dieser Klick einen bisher nicht leeren Pool leeren? (Im Projekt-Pool heißt leer „keine Einschränkung“.) */
export function wouldEmpty(before: string[], after: string[]): boolean {
  return before.length > 0 && after.length === 0
}
