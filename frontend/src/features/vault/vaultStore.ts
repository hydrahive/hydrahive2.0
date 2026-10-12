// Vault-Zustand im Browser (docs/specs/vault.md §4.3).
// Der Vault-Token liegt im sessionStorage: überlebt Neuladen im selben Tab, ist beim Schließen des Tabs weg.
// Die eigentliche Sperre macht der Server (15 min Pause, max 8 h, „Sperren“ macht alle Tokens ungültig).
import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"

interface VaultState {
  token: string | null
  /** Ein Vault-Bereich hat 423 gemeldet → PIN-Dialog zeigen. pinSet=false → „PIN festlegen“. */
  prompt: { pinSet: boolean } | null
  setToken: (t: string | null) => void
  requestUnlock: (pinSet: boolean) => void
  closePrompt: () => void
}

export const useVaultStore = create<VaultState>()(
  persist(
    (set) => ({
      token: null,
      prompt: null,
      setToken: (token) => set({ token }),
      requestUnlock: (pinSet) => set({ prompt: { pinSet } }),
      closePrompt: () => set({ prompt: null }),
    }),
    {
      name: "hh-vault",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (s) => ({ token: s.token }),
    },
  ),
)

/** Codes, bei denen 401 NICHT „ausgeloggt“ heißt (falsches Passwort/falsche PIN im Vault-Dialog). */
export const VAULT_401_CODES = new Set(["vault_pin_wrong", "invalid_credentials"])
