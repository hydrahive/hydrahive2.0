import type { ReactNode } from "react"
import type { HelpTopic } from "@/i18n/help/loader"
import { AreaTopbar } from "@/features/startdesk/AreaTopbar"

interface Props {
  /** Kern-Cockpit-Id oder Pfad – bestimmt nur noch das Hilfe-Thema; den Bereich findet die Leiste selbst. */
  active: "projects" | "buddy" | "media" | "vault" | "admin" | (string & {})
  /** Früher Kontext-Text der alten Leiste; die Bereichs-Leiste zeigt ihn nicht mehr (Schnittstelle bleibt für Module). */
  context?: string
  action?: { label: string; path: string }
  extraActions?: ReactNode
}

const HELP: Record<string, HelpTopic> = {
  projects: "projects", buddy: "buddy", media: "atelier", vault: "patientenakte", admin: "system",
}

/**
 * Obere Leiste aller Cockpit-Seiten und Module. Seit docs/specs/startdesktop.md die Bereichs-Leiste
 * (⌂ Start · Bereich ▾ · Apps des Bereichs · Kasten). Name und Props bleiben, weil Module sie importieren.
 */
export function CockpitTopbar({ active, action, extraActions }: Props) {
  return <AreaTopbar action={action} extraActions={extraActions} help={HELP[active] ?? "onboarding"} />
}
