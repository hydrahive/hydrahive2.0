// Aktiver Bereich und zuletzt benutzte App je Bereich – am Server (docs/specs/startdesktop.md, Punkt 5).
// Einmal pro Anmeldung laden. Vor dem Laden wird nur lokal vorgemerkt und danach mit dem Server-Stand
// zusammengeführt (sonst überschrieb ein Direktaufruf die Merker der anderen Bereiche – Nachtrag im Spec).
import { useEffect } from "react"
import { create } from "zustand"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { preferencesApi } from "@/features/preferences/api"

interface State {
  active: string | null
  last: Record<string, string>
  loadedFor: string | null
  /** Server-Stand ist da (oder Laden gescheitert) – ab jetzt wird direkt gespeichert. */
  loaded: boolean
  /** Lokale Änderungen vor dem Laden, die nach dem Laden gespeichert werden müssen. */
  dirty: boolean
  load: (token: string) => Promise<void>
  setActive: (id: string) => void
  remember: (id: string, path: string) => void
}

const save = (active: string | null, last: Record<string, string>) => {
  preferencesApi.patch({ active_area: active ?? undefined, area_last: last }).catch(() => { /* leise – nur Komfort */ })
}

export const useAreaPrefsStore = create<State>()((set, get) => {
  /** Änderung übernehmen: nach dem Laden sofort speichern, davor nur vormerken. */
  const apply = (active: string | null, last: Record<string, string>) => {
    set({ active, last })
    if (get().loaded) save(active, last)
    else set({ dirty: true })
  }
  return {
    active: null,
    last: {},
    loadedFor: null,
    loaded: false,
    dirty: false,
    load: async (token) => {
      if (get().loadedFor === token) return
      set({ loadedFor: token })
      try {
        const p = await preferencesApi.get()
        const { active, last, dirty } = get()
        const merged = { ...(p.area_last ?? {}), ...last }
        const nextActive = dirty ? (active ?? p.active_area ?? null) : (p.active_area ?? null)
        set({ active: nextActive, last: merged, loaded: true, dirty: false })
        if (dirty) save(nextActive, merged)
      } catch {
        set({ loaded: true, dirty: false })
      }
    },
    setActive: (id) => {
      if (get().active === id) return
      apply(id, get().last)
    },
    remember: (id, path) => {
      const { active, last } = get()
      if (active === id && last[id] === path) return
      apply(id, { ...last, [id]: path })
    },
  }
})

export function useAreaPrefs() {
  const token = useAuthStore((s) => s.token)
  const state = useAreaPrefsStore()
  useEffect(() => { if (token) void state.load(token) }, [token]) // eslint-disable-line react-hooks/exhaustive-deps
  return state
}
