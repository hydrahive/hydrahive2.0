import { parseTab, type AdminTab } from "@/features/cockpit/admin/ui"
import type { ArchiveStatus, OrphanScan } from "./api"

/** Reiter des Archiv-Fensters (Plan admin-reiter-archiv): Speicher, Vorgänge, Inhalt. Steht in der Adresse (`tab=`). */
export const ARCHIVE_TABS = ["speicher", "vorgaenge", "inhalt"] as const
export type ArchiveTab = (typeof ARCHIVE_TABS)[number]

export function parseArchiveTab(wert: string | null): ArchiveTab {
  return parseTab(ARCHIVE_TABS, wert)
}

/** Punkt bei „Vorgänge“, wenn gerade etwas läuft oder wartet bzw. Waisen gefunden sind – sichtbar aus jedem Reiter. */
function vorgaengeBrauchenBlick(status: ArchiveStatus | null, waisen: OrphanScan | null): boolean {
  const laeuft = !!status?.jobs?.running || !!status?.jobs?.queued.length || !!status?.move?.running
  const verwaist = !!waisen && waisen.workspaces.length + waisen.agents.length > 0
  return laeuft || verwaist
}

export function archiveTabs(status: ArchiveStatus | null, waisen: OrphanScan | null, eintraege: number,
  t: (key: string) => string): AdminTab<ArchiveTab>[] {
  return [
    { id: "speicher", label: t("tabs.speicher") },
    { id: "vorgaenge", label: t("tabs.vorgaenge"), dot: vorgaengeBrauchenBlick(status, waisen) },
    { id: "inhalt", label: t("tabs.inhalt"), count: eintraege },
  ]
}
