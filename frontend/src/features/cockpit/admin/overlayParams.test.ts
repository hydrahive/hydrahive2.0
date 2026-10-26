// Plan docs/plans/admin-luecken-schliessen.md, Task 6: Fensterwechsel räumt fensterbezogene URL-Teile weg.
import { describe, expect, it } from "vitest"
import { nextOverlayParams } from "./overlayParams"

const p = (q: string) => new URLSearchParams(q)

describe("nextOverlayParams", () => {
  it("Schließen entfernt section, tab und container", () => {
    expect(nextOverlayParams(p("section=federation&tab=clients"), null).toString()).toBe("")
  })
  it("anderes Fenster öffnen: kein Reiter des alten Fensters bleibt hängen", () => {
    expect(nextOverlayParams(p("section=federation&tab=peers"), "llm").toString()).toBe("section=llm")
  })
  it("fremde Parameter bleiben erhalten", () => {
    expect(nextOverlayParams(p("foo=1&container=abc"), "users").toString()).toBe("foo=1&section=users")
  })
  it("verändert die übergebenen Parameter nicht", () => {
    const before = p("section=federation&tab=peers")
    nextOverlayParams(before, null)
    expect(before.toString()).toBe("section=federation&tab=peers")
  })
})
