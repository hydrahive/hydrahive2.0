import type { ModuleEntry } from "@/features/modules/types"
import { parseTab, type AdminTab } from "./ui"

/** Reiter des Module-Fensters (Plan admin-reiter-module). Steht in der Adresse (`tab=`). */
export const MODULE_TABS = ["installiert", "verfuegbar"] as const
export type ModuleTab = (typeof MODULE_TABS)[number]

export function parseModuleTab(wert: string | null): ModuleTab {
  return parseTab(MODULE_TABS, wert)
}

const kaputt = (m: ModuleEntry) => m.installed && (!m.loaded || !!m.error)

function passt(m: ModuleEntry, query: string): boolean {
  const q = query.trim().toLowerCase()
  if (!q) return true
  return [m.name, m.id, m.description].some((feld) => feld.toLowerCase().includes(q))
}

/** Rang: Fehler zuerst, dann Update, dann der Rest. */
const rang = (m: ModuleEntry) => (kaputt(m) ? 0 : m.update_available ? 1 : 2)

/**
 * Module eines Reiters, gefiltert und sortiert. `pinned`: Kennung → Reiter, in dem in dieser Sitzung eine Aktion lief.
 * Solche Module bleiben dort, damit Protokoll und Erfolg nicht mit der Karte in den anderen Reiter wandern.
 */
export function moduleView(modules: ModuleEntry[], tab: ModuleTab, query: string,
  pinned: ReadonlyMap<string, ModuleTab> = new Map()): ModuleEntry[] {
  const reiterVon = (m: ModuleEntry): ModuleTab => pinned.get(m.id) ?? (m.installed ? "installiert" : "verfuegbar")
  return modules
    .filter((m) => reiterVon(m) === tab && passt(m, query))
    .sort((a, b) => rang(a) - rang(b) || a.name.localeCompare(b.name, "de"))
}

export function moduleTabs(modules: ModuleEntry[], query: string, t: (key: string) => string): AdminTab<ModuleTab>[] {
  const installiert = moduleView(modules, "installiert", query)
  return [
    { id: "installiert", label: t("tabs.installiert"), count: installiert.length,
      dot: modules.some((m) => m.installed && (m.update_available || kaputt(m))) },
    { id: "verfuegbar", label: t("tabs.verfuegbar"), count: moduleView(modules, "verfuegbar", query).length },
  ]
}
