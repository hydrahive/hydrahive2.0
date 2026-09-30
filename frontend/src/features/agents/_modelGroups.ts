import type { RegistryModel } from "@/features/llm/api"
import { providerName } from "@/features/llm/_llm_providers"

export interface ModelFilter {
  query: string
  onlyFree: boolean
  /** Leer = alle Anbieter. */
  provider: string
}

export interface ModelGroup {
  provider: string
  name: string
  models: RegistryModel[]
}

const byName = (a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name)

/**
 * Filtert und gruppiert die Modelle für den Agent-Editor nach Anbieter.
 * Bewusst OHNE Limit: Ein globales `.slice(0, 100)` hat nach der
 * Provider-Sortierung ganze Anbieter (OpenRouter, Codex) unsichtbar gemacht
 * (Task 19687316).
 */
export function groupModels(catalog: RegistryModel[], filter: ModelFilter): ModelGroup[] {
  const q = filter.query.trim().toLowerCase()
  const groups = new Map<string, RegistryModel[]>()
  for (const model of catalog) {
    if (filter.onlyFree && model.is_free !== true) continue
    if (filter.provider && model.provider !== filter.provider) continue
    if (q && !model.id.toLowerCase().includes(q) && !model.label.toLowerCase().includes(q)) continue
    const key = model.provider || "unknown"
    const list = groups.get(key) ?? []
    list.push(model)
    groups.set(key, list)
  }
  return [...groups.entries()]
    .map(([provider, models]) => ({
      provider,
      name: providerName(provider),
      models: models.sort((a, b) => a.id.localeCompare(b.id)),
    }))
    .sort(byName)
}

/** Anbieter mit Anzahl Modelle, für den Anbieter-Filter. */
export function providersOf(catalog: RegistryModel[]): { provider: string; name: string; count: number }[] {
  const counts = new Map<string, number>()
  for (const model of catalog) {
    const key = model.provider || "unknown"
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([provider, count]) => ({ provider, name: providerName(provider), count }))
    .sort(byName)
}
