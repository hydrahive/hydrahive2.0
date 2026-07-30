import { useCallback, useState } from "react"
import type { useUserPreferences } from "@/features/preferences/useUserPreferences"

const PREF_KEY = "project_selected_agent"

type Prefs = ReturnType<typeof useUserPreferences>

/**
 * Merkt sich pro Projekt, welcher Agent gewählt ist — F5-fest.
 *
 * Vorher lag die Auswahl in reinem useState: nach einem Reload war sie weg und
 * die Ableitung fiel auf den Projekt-Agenten zurück. Wer mit einem
 * Spezialisten arbeitete, landete nach F5 im Chat des Projekt-Agenten.
 *
 * Gespeichert wird in `cockpit_layout` (bereits vorhandenes generisches
 * UI-Zustands-Objekt), damit kein neues Preferences-Feld nötig ist — das
 * Backend-Schema hat `extra="forbid"`.
 *
 * Gelesen wird direkt aus den Preferences (kein Hydration-Effekt). Lokale
 * Overrides gewinnen, damit ein Klick sofort wirkt und nicht auf den
 * Server-Roundtrip wartet — und damit eine verzögert eintreffende
 * Server-Antwort die frische Auswahl nicht wieder überschreibt.
 */
export function useProjectAgentSelection(prefs: Prefs) {
  const [overrides, setOverrides] = useState<Record<string, string>>({})

  const stored = prefs.preferences.cockpit_layout?.[PREF_KEY]
  const persisted = (stored && typeof stored === "object" ? stored : {}) as Record<string, string>
  const selectedByProject = { ...persisted, ...overrides }

  const select = useCallback((projectId: string, agentId: string) => {
    setOverrides((cur) => ({ ...cur, [projectId]: agentId }))
    const current = prefs.preferences.cockpit_layout?.[PREF_KEY]
    const base = (current && typeof current === "object" ? current : {}) as Record<string, string>
    void prefs.patch({
      cockpit_layout: {
        ...prefs.preferences.cockpit_layout,
        [PREF_KEY]: { ...base, [projectId]: agentId },
      },
    }).catch(() => {
      // Persistenz ist Komfort, kein Muss: die Auswahl gilt lokal weiter.
    })
  }, [prefs])

  return { selectedByProject, select }
}
