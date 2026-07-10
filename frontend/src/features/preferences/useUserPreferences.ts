import { useCallback, useEffect, useState } from "react"
import { preferencesApi, type UserPreferences, type UserPreferencesPatch } from "./api"

const DEFAULT_PREFS: UserPreferences = {
  active_project_id: null,
  active_media_project_id: null,
  active_vault_scope: "private",
  cockpit_layout: {},
}

export function useUserPreferences() {
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setPreferences(await preferencesApi.get())
    } catch (err) {
      setError(err instanceof Error ? err.message : "preferences_load_failed")
    } finally {
      setLoading(false)
    }
  }, [])

  const patch = useCallback(async (changes: UserPreferencesPatch) => {
    setError(null)
    const updated = await preferencesApi.patch(changes)
    setPreferences(updated)
    return updated
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  return { preferences, loading, error, reload, patch }
}
