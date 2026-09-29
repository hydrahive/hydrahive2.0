import { create } from "zustand"
import { useEffect } from "react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { accessApi } from "./api"
import type { MyAccess } from "./types"

// Eigene Freigaben einmal pro Anmeldung laden. Solange nichts geladen ist,
// sperrt die Oberfläche nichts (das Backend schützt ohnehin mit 403).
interface State {
  access: MyAccess | null
  loadedFor: string | null
  load: (token: string) => Promise<void>
  reset: () => void
}

export const useMyAccessStore = create<State>()((set, get) => ({
  access: null,
  loadedFor: null,
  load: async (token) => {
    if (get().loadedFor === token) return
    set({ loadedFor: token })
    try { set({ access: await accessApi.me() }) } catch { set({ access: null }) }
  },
  reset: () => set({ access: null, loadedFor: null }),
}))

export function useMyAccess(): MyAccess | null {
  const token = useAuthStore((s) => s.token)
  const access = useMyAccessStore((s) => s.access)
  const load = useMyAccessStore((s) => s.load)
  const reset = useMyAccessStore((s) => s.reset)
  useEffect(() => {
    if (token) void load(token)
    else reset()
  }, [token, load, reset])
  return token ? access : null
}
