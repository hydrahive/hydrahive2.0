import { api } from "@/shared/api-client"

export type VaultScope = "private" | "family" | "business"

export interface UserPreferences {
  active_project_id: string | null
  active_media_project_id: string | null
  active_vault_scope: VaultScope
  cockpit_layout: Record<string, unknown>
  /** Startseite nach dem Anmelden (docs/specs/startdesktop.md). */
  landing: "start" | "buddy" | "dashboard"
  /** Zuletzt aktiver Bereich der Bereichs-Leiste. */
  active_area: string | null
  /** Bereich → zuletzt benutzter Pfad. */
  area_last: Record<string, string>
}

export type UserPreferencesPatch = Partial<UserPreferences>

export const preferencesApi = {
  get: () => api.get<UserPreferences>("/me/preferences"),
  patch: (patch: UserPreferencesPatch) => api.patch<UserPreferences>("/me/preferences", patch),
}
