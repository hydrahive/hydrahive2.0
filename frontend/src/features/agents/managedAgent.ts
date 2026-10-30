/** Verwaltete Agenten (docs/specs/projekt-container-ausfuehrung.md, K1c): ein Modul legt sie an und hält
 * Werkzeuge, Prompt und Soul fest. In der Oberfläche bleiben nur Übersicht, Modell und Intervalle. */
export const MANAGED_TABS = new Set(["overview", "model", "schedules"])

export function isManaged(agent: { managed_by?: string | null }): boolean {
  return typeof agent.managed_by === "string" && agent.managed_by.length > 0
}

export function visibleTabs<T extends { id: string }>(tabs: T[], agent: { managed_by?: string | null }): T[] {
  return isManaged(agent) ? tabs.filter((t) => MANAGED_TABS.has(t.id)) : tabs
}

/** Gewählter Reiter, oder „overview“, wenn er nicht (mehr) angeboten wird (verwaltete Agenten, Mail weg). */
export function activeTabFor(tab: string, tabs: { id: string }[], hasMail: boolean): string {
  return !tabs.some((x) => x.id === tab) || (!hasMail && tab === "mail") ? "overview" : tab
}
