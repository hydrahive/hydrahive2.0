import type { Area } from "./types"

/**
 * Helfer-Pool aus eingeschalteten Bereichen (AB7, Spec 4.4): die TOOL-NAMEN der eingeschalteten Bereiche – nie kategorie:x –
 * ohne alles, was nie per Auftrag vergeben wird (``forbidden``: Shell-Sperre, Authoring, ask_agent, Katalog-Werkzeuge).
 * Reihenfolge stabil (Bereiche in der gegebenen Reihenfolge), ohne Dubletten, unbekannte Bereiche werden ignoriert.
 */
export function helperPoolItems(areas: Area[], enabledIds: string[], forbidden: string[]): string[] {
  const never = new Set(forbidden)
  const on = new Set(enabledIds)
  const out: string[] = []
  for (const a of areas) {
    if (!on.has(a.id)) continue
    for (const t of a.tools) if (!never.has(t) && !t.startsWith("kategorie:") && !out.includes(t)) out.push(t)
  }
  return out
}

/** Ein Bereich, von dem nichts per Auftrag vergeben werden darf (alle Tools in ``forbidden``, oder keine) → ausgegraut. */
export function neverGiven(area: Area, forbidden: string[]): boolean {
  const never = new Set(forbidden)
  return area.tools.every((t) => never.has(t) || t.startsWith("kategorie:"))
}

/** Welche Bereiche stecken (ganz oder teilweise) im gespeicherten Pool? Ein Bereich zählt als an, wenn alle seine vergebbaren Tools drin sind. */
export function enabledFromPool(areas: Area[], items: string[], forbidden: string[]): string[] {
  const have = new Set(items)
  const never = new Set(forbidden)
  return areas.filter((a) => {
    const giveable = a.tools.filter((t) => !never.has(t))
    return giveable.length > 0 && giveable.every((t) => have.has(t))
  }).map((a) => a.id)
}

/** Pool-Einträge, die keinem ganz eingeschalteten Bereich angehören (kategorie:x, einzelne Tools) – bleiben beim Speichern. */
export function extraPoolItems(areas: Area[], items: string[], forbidden: string[]): string[] {
  const covered = new Set<string>()
  for (const id of enabledFromPool(areas, items, forbidden)) for (const t of areas.find((a) => a.id === id)?.tools ?? []) covered.add(t)
  return items.filter((i) => !covered.has(i))
}
