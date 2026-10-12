import { beforeEach, describe, expect, it, vi } from "vitest"

// Node hat kein Web-Storage: vor dem Import der Stores eigene Speicher anlegen (persist liest sie beim Erzeugen).
const stores = vi.hoisted(() => {
  function mem() {
    const m = new Map<string, string>()
    return {
      getItem: (k: string) => (m.has(k) ? m.get(k)! : null),
      setItem: (k: string, v: string) => { m.set(k, String(v)) },
      removeItem: (k: string) => { m.delete(k) },
      clear: () => m.clear(),
      dump: () => JSON.stringify([...m.entries()]),
    }
  }
  const session = mem()
  const local = mem()
  Object.defineProperty(globalThis, "sessionStorage", { configurable: true, value: session })
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: local })
  return { session, local }
})

import { useAuthStore } from "@/features/auth/useAuthStore"
import { useVaultStore } from "./vaultStore"

describe("Vault-Store", () => {
  beforeEach(() => {
    stores.session.clear()
    stores.local.clear()
    useVaultStore.setState({ token: null, prompt: null })
  })

  it("legt den Token nur im sessionStorage ab (Tab zu = gesperrt)", () => {
    useVaultStore.getState().setToken("vt-x")
    expect(stores.session.getItem("hh-vault")).toContain("vt-x")
    expect(stores.local.dump()).not.toContain("vt-x")
  })

  it("speichert den PIN-Dialog-Zustand nicht", () => {
    useVaultStore.getState().requestUnlock(true)
    expect(stores.session.getItem("hh-vault") ?? "").not.toContain("pinSet")
  })

  it("Ausloggen wirft die Entsperrung weg", () => {
    useAuthStore.setState({ token: "jwt", username: "u", role: "user" })
    useVaultStore.getState().setToken("vt-y")
    expect(stores.session.getItem("hh-vault")).toContain("vt-y")
    useAuthStore.getState().logout()
    expect(stores.session.getItem("hh-vault")).toBeNull()
  })
})
