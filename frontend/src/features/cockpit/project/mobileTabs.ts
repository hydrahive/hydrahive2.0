// Reiter des Projekt-Cockpits unter 1280 px (Tailwind xl). Ab xl sind alle drei
// Bereiche nebeneinander sichtbar, die Reiter-Wahl wirkt dort nicht.
// Spec: docs/specs/project-cockpit-mobile-tabs.md

export const MOBILE_TABS = ["project", "chat", "files"] as const
export type MobileTab = (typeof MOBILE_TABS)[number]

/** Klassen zum Verstecken eines Bereichs unter xl. Leer, wenn er der aktive Reiter ist. */
export function paneClass(tab: MobileTab, active: MobileTab, wideDisplay: "block" | "grid"): string {
  if (tab === active) return ""
  return wideDisplay === "grid" ? "hidden xl:grid" : "hidden xl:block"
}

/** Wer einen Agenten wählt oder eine Sitzung öffnet, will mit ihm schreiben. */
export function tabAfterAgentPick(): MobileTab {
  return "chat"
}
