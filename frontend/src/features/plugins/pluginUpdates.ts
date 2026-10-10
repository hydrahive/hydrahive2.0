// Plugin-Updates anzeigen wie bei den Modulen (docs/specs/plugin-updates.md): Logik ohne React, damit testbar.
import type { InstalledPlugin } from "./types"

export type UpdateBadge = { kind: "update"; from: string; to: string } | { kind: "restart" } | null
export type HubAction = "install" | "update" | "installed"
type T = (key: string, opts?: Record<string, unknown>) => string

/** Plakette einer installierten Karte. „Neustart nötig“ geht vor: die neue Version liegt schon auf der Platte. */
export function updateBadge(p: InstalledPlugin): UpdateBadge {
  if (p.restart_needed) return { kind: "restart" }
  if (p.update_available && p.available_version) {
    return { kind: "update", from: p.installed_version ?? p.version ?? "?", to: p.available_version }
  }
  return null
}

/** Plugins, die „Alle updaten“ aktualisiert (ohne die, die nur noch einen Neustart brauchen). */
export function outdatedNames(list: InstalledPlugin[]): string[] {
  return list.filter((p) => updateBadge(p)?.kind === "update").map((p) => p.name)
}

/** Was der Knopf einer Hub-Karte tut: installieren, aktualisieren oder nichts (installiert und aktuell). */
export function hubCardAction(name: string, installed: Map<string, InstalledPlugin>): HubAction {
  const p = installed.get(name)
  if (!p) return "install"
  return updateBadge(p)?.kind === "update" ? "update" : "installed"
}

/** „Installiert (4)“ bzw. „Installiert (4 · 1 Update)“. */
export function installedTabLabel(t: T, total: number, updates: number): string {
  return updates > 0 ? `${t("tab_installed")} (${total} · ${t("update_count", { count: updates })})`
    : `${t("tab_installed")} (${total})`
}
