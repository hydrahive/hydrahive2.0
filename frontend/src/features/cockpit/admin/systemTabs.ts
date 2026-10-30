import type { HealthCheck } from "@/features/system/api"
import { parseTab, type AdminTab } from "./ui"

/** Reiter des System-Fensters (Plan admin-reiter-system). Steht in der Adresse (`tab=`). */
const ALLE = ["ueberblick", "netzwerk", "erweiterungen", "sicherung"] as const
export type SystemTab = (typeof ALLE)[number]

/** Nicht-Admins sehen nur Überblick und AgentLink – ihre anderen Reiter wären leer. */
export function systemTabList(isAdmin: boolean): readonly SystemTab[] {
  return isAdmin ? ALLE : ALLE.slice(0, 2)
}

export function parseSystemTab(wert: string | null, isAdmin: boolean): SystemTab {
  return parseTab(systemTabList(isAdmin), wert)
}

export function systemTabs(checks: HealthCheck[], isAdmin: boolean, t: (key: string) => string): AdminTab<SystemTab>[] {
  return systemTabList(isAdmin).map((id) => ({
    id,
    label: t(`tabs.${id}`),
    ...(id === "ueberblick" ? { dot: checks.some((c) => !c.ok) } : {}),
  }))
}
