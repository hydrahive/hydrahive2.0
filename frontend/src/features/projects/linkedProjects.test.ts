import { describe, expect, it } from "vitest"
import { linkCandidates, linksChanged, toggleLink } from "./linkedProjects"
import type { Project, ProjectRole } from "./types"

const p = (id: string, name: string, members: [string, ProjectRole][] = [], created_by = "x") =>
  ({ id, name, created_by, members: members.map(([username, role]) => ({ username, role })) } as Project)

describe("verknüpfte Projekte", () => {
  it("System-Admin: alle anderen Projekte, alphabetisch, ohne das eigene", () => {
    const all = [p("c", "Zeta"), p("a", "HydraVR"), p("b", "Alpha")]
    expect(linkCandidates(all, "a", { username: "till", role: "admin" }, []).map((x) => x.id)).toEqual(["b", "c"])
  })
  it("Nutzer: nur Projekte mit Schreibrecht (write, admin, Ersteller) – lesen reicht nicht (wie der Server)", () => {
    const all = [p("r", "Nur lesen", [["till", "read"]]), p("w", "Schreiben", [["till", "write"]]),
                 p("ad", "Admin", [["till", "admin"]]), p("own", "Eigenes", [], "till"), p("f", "Fremd")]
    expect(linkCandidates(all, "self", { username: "till", role: "user" }, []).map((x) => x.id))
      .toEqual(["ad", "own", "w"])
  })
  it("bereits verknüpfte bleiben sichtbar, auch ohne Schreibrecht – damit man sie abwählen kann", () => {
    const all = [p("r", "Nur lesen", [["till", "read"]]), p("w", "Schreiben", [["till", "write"]])]
    expect(linkCandidates(all, "self", { username: "till", role: "user" }, ["r"]).map((x) => x.id)).toEqual(["r", "w"])
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
