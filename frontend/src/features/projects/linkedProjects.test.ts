import { describe, expect, it } from "vitest"
import { linkCandidates, linksChanged, toggleLink } from "./linkedProjects"
import type { Project } from "./types"

const p = (id: string, name: string) => ({ id, name } as Project)

describe("verknüpfte Projekte", () => {
  it("bietet alle anderen Projekte an, alphabetisch, ohne das eigene", () => {
    const all = [p("c", "Zeta"), p("a", "HydraVR"), p("b", "Alpha")]
    expect(linkCandidates(all, "a").map((x) => x.id)).toEqual(["b", "c"])
  })
  it("schaltet an und aus, Reihenfolge der Auswahl bleibt", () => {
    expect(toggleLink([], "x")).toEqual(["x"])
    expect(toggleLink(["x", "y"], "x")).toEqual(["y"])
    expect(toggleLink(["y"], "x")).toEqual(["y", "x"])
  })
  it("erkennt Änderungen unabhängig von der Reihenfolge", () => {
    expect(linksChanged(["a", "b"], ["b", "a"])).toBe(false)
    expect(linksChanged(["a"], ["a", "b"])).toBe(true)
    expect(linksChanged(["a"], ["b"])).toBe(true)
    expect(linksChanged([], [])).toBe(false)
  })
})
