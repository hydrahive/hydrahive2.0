import { describe, expect, it } from "vitest"
import { MOBILE_TABS, paneClass, tabAfterAgentPick } from "./mobileTabs"

// Task 1841e0df: Unter 1280 px (xl) zeigte /projects alle drei Bereiche gestapelt,
// der Chat bekam 68–104 px. Unter xl ist jetzt nur der gewählte Reiter sichtbar.
describe("mobileTabs", () => {
  it("kennt genau die drei Reiter in fester Reihenfolge, Chat in der Mitte", () => {
    expect(MOBILE_TABS).toEqual(["project", "chat", "files"])
  })

  it("aktiver Bereich bekommt keine Versteck-Klasse", () => {
    expect(paneClass("chat", "chat", "block")).toBe("")
    expect(paneClass("files", "files", "grid")).toBe("")
  })

  it("inaktiver Bereich ist unter xl versteckt und ab xl sichtbar (block)", () => {
    const c = paneClass("project", "chat", "block").split(" ")
    expect(c).toContain("hidden")
    expect(c).toContain("xl:block")
    expect(c).not.toContain("xl:grid")
  })

  it("inaktiver Bereich mit Raster wird ab xl wieder zum Raster", () => {
    const c = paneClass("files", "project", "grid").split(" ")
    expect(c).toContain("hidden")
    expect(c).toContain("xl:grid")
    expect(c).not.toContain("xl:block")
  })

  it("Agent wählen führt immer in den Chat", () => {
    expect(tabAfterAgentPick()).toBe("chat")
  })
})
