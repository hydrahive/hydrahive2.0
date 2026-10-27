// Plan docs/plans/meine-einstellungen-kompakt.md, Task 1: gewählter Agent/Projekt steht in der URL (?item=).
import { describe, expect, it } from "vitest"
import { selectedItem, withItem } from "./settingsTabs"

describe("selectedItem / withItem", () => {
  it("liest die Auswahl", () => {
    expect(selectedItem("?item=a1")).toBe("a1")
    expect(selectedItem("")).toBeNull()
  })
  it("setzt die Auswahl und lässt andere Parameter stehen", () => {
    expect(withItem("?x=1", "b2")).toBe("?x=1&item=b2")
    expect(withItem("?item=a", "b")).toBe("?item=b")
  })
  it("entfernt die Auswahl", () => {
    expect(withItem("?item=a", null)).toBe("")
  })
})
