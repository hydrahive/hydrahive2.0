import { describe, expect, it } from "vitest"
import { charImageForGroup } from "./officeAssets"

describe("charImageForGroup (Spec agent-office.md §4.1)", () => {
  it("liefert das Bild der passenden Template-Gruppe", () => {
    expect(charImageForGroup("personal")).toBe("/office-media/char-personal.webp")
    expect(charImageForGroup("projects")).toBe("/office-media/char-projects.webp")
    expect(charImageForGroup("specialists")).toBe("/office-media/char-specialists.webp")
    expect(charImageForGroup("modules")).toBe("/office-media/char-modules.webp")
    expect(charImageForGroup("system")).toBe("/office-media/char-system.webp")
  })

  it("fällt bei unbekannter oder fehlender Gruppe auf specialists zurück", () => {
    expect(charImageForGroup(undefined)).toBe("/office-media/char-specialists.webp")
    expect(charImageForGroup("unbekannt")).toBe("/office-media/char-specialists.webp")
  })
})
