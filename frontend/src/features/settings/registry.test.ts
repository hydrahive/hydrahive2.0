// Plan docs/plans/meine-einstellungen.md, Task 2: „Meine Einstellungen“ zeigt nur, was jeder Nutzer selbst einstellt.
import { describe, expect, it, vi } from "vitest"

vi.mock("react", async (orig) => ({ ...(await orig<typeof import("react")>()), lazy: () => () => null }))
import { SETTINGS_GROUPS } from "./registry"
import { ADMIN_GROUP_TARGET } from "./legacyRedirects"

describe("Meine Einstellungen: Gruppen", () => {
  it("genau die sechs persönlichen Gruppen, in dieser Reihenfolge", () => {
    expect(SETTINGS_GROUPS.map((g) => g.id)).toEqual(["agents", "projects", "communication", "credentials", "skills", "butler"])
  })
  it("keine Gruppe hat ein Zuhause im Admin-Cockpit", () => {
    const admin = Object.keys(ADMIN_GROUP_TARGET)
    expect(SETTINGS_GROUPS.filter((g) => admin.includes(g.id))).toEqual([])
  })
  it("keine Gruppe ist nur für Admins", () => {
    expect(SETTINGS_GROUPS.filter((g) => g.adminOnly)).toEqual([])
  })
})
