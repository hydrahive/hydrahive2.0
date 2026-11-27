import { toggle } from "./toggle"
import type { AreaCatalog, AreaStatus } from "./types"

/** Tools, die der Entwurf nur über ``kategorie:x`` bekommt (aufgelöst über ``catalog.categories``). */
export function viaCategory(tools: string[], categories: Record<string, string[]> | undefined): Set<string> {
  const out = new Set<string>()
  for (const t of tools) {
    if (!t.startsWith("kategorie:")) continue
    for (const n of categories?.[t.slice(10)] ?? []) out.add(n)
  }
  return out
}

/**
 * Spiegel von agents/area_state.py::area_states für den ENTWURF (draft.tools) – muss sich gleich verhalten:
 * have = einzeln da, via_category = nur über kategorie:x (aus dem Entwurf, Review #794), missing = weder noch,
 * new = vom Server (gesehener Stand) ∩ missing; on = einzeln da und missing ⊆ new; partial = sonst, wenn etwas da ist; off.
 * „new“ nur bei on (Spec 4.3).
 */
export function overlay(catalog: AreaCatalog, status: AreaStatus, tools: string[]): AreaStatus {
  const have = new Set(tools)
  const via = viaCategory(tools, catalog.categories)
  return {
    editable: status.editable,
    areas: status.areas.map((s) => {
      const area = catalog.areas.find((a) => a.id === s.id)
      if (!area || area.tools.length === 0) return s
      const mine = area.tools.filter((t) => have.has(t))
      const viaCat = area.tools.filter((t) => via.has(t) && !have.has(t))
      const missing = area.tools.filter((t) => !have.has(t) && !via.has(t))
      const keep = s.new.filter((t) => missing.includes(t))
      const state = mine.length > 0 && missing.every((t) => keep.includes(t)) ? "on" : mine.length > 0 || viaCat.length > 0 ? "partial" : "off"
      return { ...s, state, have: mine, missing, via_category: viaCat, new: state === "on" ? keep : [] }
    }),
  }
}

/** Mehrere Bereiche in EINEM Schritt einschalten (sonst gewinnt bei zusammengeführten Patches nur der letzte, Review #794). */
export function applyMany(tools: string[], catalog: AreaCatalog, ids: string[]): string[] {
  const byId = new Map(catalog.areas.map((a) => [a.id, a]))
  return ids.reduce((acc, id) => toggle(acc, byId.get(id)?.tools ?? [], true), tools)
}
