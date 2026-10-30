import { parseTab } from "./ui"

/** Reiter des Benutzer-Fensters (Plan admin-reiter-benutzer). Steht in der Adresse (`tab=`). */
export const USERS_TABS = ["benutzer", "gruppen", "api-keys"] as const
export type UsersTab = (typeof USERS_TABS)[number]

export function parseUsersTab(wert: string | null): UsersTab {
  return parseTab(USERS_TABS, wert)
}
