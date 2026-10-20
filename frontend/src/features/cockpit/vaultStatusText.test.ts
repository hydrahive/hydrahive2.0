import { describe, expect, it } from "vitest"
import { VAULT_ACTIVE, VAULT_PLANNED } from "./vaultStatusText"

// Ehrlicher Status (Stand Vault V1, 20.10.2026): was aktiv ist, muss im Code belegt sein; Geplantes steht nicht als aktiv da.
describe("Vault-Status", () => {
  it("nennt die PIN-Sperre als aktiv – mit 15 Minuten wie tokens.IDLE_SECONDS", () => {
    const pin = VAULT_ACTIVE.find((t) => t.includes("PIN"))
    expect(pin).toBeDefined()
    expect(pin).toContain("15 Minuten")
  })

  it("sagt ehrlich, dass Buddy-Werkzeuge ohne PIN laufen (Spec vault.md §3)", () => {
    expect(VAULT_ACTIVE.some((t) => /Buddy/.test(t) && /ohne PIN|auch bei gesperrtem/.test(t))).toBe(true)
  })

  it("führt Protokoll und Vault-Chat als geplant, nicht als aktiv", () => {
    expect(VAULT_ACTIVE.some((t) => /Protokoll|Vault-Chat/.test(t))).toBe(false)
    expect(VAULT_PLANNED.some((t) => t.includes("Protokoll"))).toBe(true)
    expect(VAULT_PLANNED.some((t) => t.includes("Vault-Chat"))).toBe(true)
  })

  it("verspricht die PIN nicht mehr als geplant", () => {
    expect(VAULT_PLANNED.some((t) => t.includes("PIN"))).toBe(false)
  })
})
