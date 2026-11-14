import { describe, expect, it } from "vitest"
import { charImageForGroup } from "./officeAssets"

describe("charImageForGroup (Spec agent-office.md §4.1)", () => {
  it("liefert das Bild der passenden Template-Gruppe", () => {
    expect(charImageForGroup("personal")).toBe("/office/char-personal.webp")
    expect(charImageForGroup("projects")).toBe("/office/char-projects.webp")
    expect(charImageForGroup("specialists")).toBe("/office/char-specialists.webp")
    expect(charImageForGroup("modules")).toBe("/office/char-modules.webp")
    expect(charImageForGroup("system")).toBe("/office/char-system.webp")
  })

  it("fällt bei unbekannter oder fehlender Gruppe auf specialists zurück", () => {
    expect(charImageForGroup(undefined)).toBe("/office/char-specialists.webp")
    expect(charImageForGroup("unbekannt")).toBe("/office/char-specialists.webp")
  })
})
