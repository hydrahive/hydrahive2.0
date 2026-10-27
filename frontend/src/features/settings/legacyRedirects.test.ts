// Plan docs/plans/meine-einstellungen.md, Task 1: alte Hub-Adressen für Admin-Dinge leiten ins Admin-Cockpit.
import { describe, expect, it } from "vitest"
import { isAdminOverlayId } from "@/features/cockpit/admin/adminOverlayRegistry"
import { ADMIN_GROUP_TARGET, legacyTarget } from "./legacyRedirects"

describe("legacyTarget", () => {
  it.each([
    ["modules", "/admin?section=modules"], ["plugins", "/admin?section=plugins"],
    ["themes", "/admin?section=themes"], ["extensions", "/admin?section=extensions"],
    ["mcp", "/admin?section=mcp"], ["llm", "/admin?section=llm"],
    ["federation", "/admin?section=federation"], ["connections", "/admin?section=system"],
    ["system", "/admin?section=system"], ["settings_values", "/admin?section=system-settings"],
    ["users", "/admin?section=users"], ["zahnfee", "/admin?section=zahnfee"],
  ])("%s → %s", (group, target) => {
    expect(legacyTarget(group)).toBe(target)
  })

  it.each(["agents", "projects", "communication", "skills", "butler", "credentials", "xyz", "toString", "constructor", undefined])(
    "%s bleibt im Hub", (group) => {
      expect(legacyTarget(group)).toBeNull()
    })

  it("jedes Ziel ist ein gültiges Admin-Fenster", () => {
    for (const target of Object.values(ADMIN_GROUP_TARGET)) {
      const section = new URL(target, "http://x").searchParams.get("section")
      expect(target.startsWith("/admin?section=")).toBe(true)
      expect(isAdminOverlayId(section)).toBe(true)
    }
  })
})
