// Aktiver Bereich und zuletzt benutzte App je Bereich – am Server (docs/specs/startdesktop.md, Punkt 5).
// Einmal pro Anmeldung laden; Änderungen sofort lokal, Server im Hintergrund (Fehler leise: nur Komfort).
import { useEffect } from "react"
import { create } from "zustand"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { preferencesApi } from "@/features/preferences/api"

interface State {
  active: string | null
  last: Record<string, string>
  loadedFor: string | null
  load: (token: string) => Promise<void>
  setActive: (id: string) => void
  remember: (id: string, path: string) => void
}

const save = (patch: { active_area?: string; area_last?: Record<string, string> }) => {
  preferencesApi.patch(patch).catch(() => { /* leise – nur Komfort */ })
}

export const useAreaPrefsStore = create<State>()((set, get) => ({
  active: null,
  last: {},
  loadedFor: null,
  load: async (token) => {
    if (get().loadedFor === token) return
    set({ loadedFor: token })
    try {
      const p = await preferencesApi.get()
      set({ active: p.active_area ?? null, last: p.area_last ?? {} })
    } catch { /* ohne Server: leer starten */ }
  },
  setActive: (id) => {
    if (get().active === id) return
    set({ active: id })
    save({ active_area: id })
  },
  remember: (id, path) => {
    const { active, last } = get()
    if (active === id && last[id] === path) return
    const next = { ...last, [id]: path }
    set({ active: id, last: next })
    save({ active_area: id, area_last: next })
  },
}))

export function useAreaPrefs() {
  const token = useAuthStore((s) => s.token)
  const state = useAreaPrefsStore()
  useEffect(() => { if (token) void state.load(token) }, [token]) // eslint-disable-line react-hooks/exhaustive-deps
  return state
}
