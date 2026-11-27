import { describe, expect, it } from "vitest"
import { mayEditPool } from "./mayEditPool"

describe("mayEditPool – Helfer-Bereich nur für Besitzer oder Admin (Review B3)", () => {
  it("Admin darf immer", () => { expect(mayEditPool("anna", "bert", "admin")).toBe(true) })
  it("Besitzer darf", () => { expect(mayEditPool("anna", "anna", "user")).toBe(true) })
  it("fremder Nutzer darf nicht", () => { expect(mayEditPool("anna", "bert", "user")).toBe(false) })
  it("ohne Besitzer oder ohne Anmeldung nicht", () => {
    expect(mayEditPool(undefined, "bert", "user")).toBe(false)
    expect(mayEditPool("anna", null, null)).toBe(false)
  })
})
