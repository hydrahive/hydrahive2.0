import { api } from "@/shared/api-client"

export type VaultScope = "private" | "family" | "business"

export interface UserPreferences {
  active_project_id: string | null
  active_media_project_id: string | null
  active_vault_scope: VaultScope
  cockpit_layout: Record<string, unknown>
}

export type UserPreferencesPatch = Partial<UserPreferences>

export const preferencesApi = {
  get: () => api.get<UserPreferences>("/me/preferences"),
  patch: (patch: UserPreferencesPatch) => api.patch<UserPreferences>("/me/preferences", patch),
}
