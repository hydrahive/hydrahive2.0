// Agenten-Bereiche, Aufgabe 7 (AB8): Bereichs-Schalter ↔ Tool-Namen. Gespeichert werden Tool-Namen, nie „kategorie:x“ oder Bereichs-IDs.
import { describe, expect, it } from "vitest"
import { applyAreas, areaIsOn, toggleArea } from "./areaItems"
import type { AreaInfo } from "./areasApi"

const area = (id: string, tools: string[]): AreaInfo =>
  ({ id, group: "g", name: id, sentence: "", marks: [], tools })
const AREAS = [area("files", ["file_read", "file_write"]), area("web", ["web_search", "ssh_exec"]), area("delegate", ["ask_agent"])]
const NEVER = new Set(["ssh_exec", "ask_agent"])

describe("areaIsOn", () => {
  it("an, wenn alle vergebbaren Tools des Bereichs im Pool stehen", () => {
    expect(areaIsOn(AREAS[0], new Set(["file_read", "file_write"]), NEVER)).toBe(true)
    expect(areaIsOn(AREAS[0], new Set(["file_read"]), NEVER)).toBe(false)
  })
  it("ein einzeln abgelehntes Tool hindert den Schalter nicht", () => {
    expect(areaIsOn(AREAS[1], new Set(["web_search"]), NEVER)).toBe(true)
  })
  it("ein Bereich ohne vergebbares Tool ist nie an", () => {
    expect(areaIsOn(AREAS[2], new Set(["ask_agent"]), NEVER)).toBe(false)
  })
})

describe("applyAreas", () => {
  it("speichert Tool-Namen der eingeschalteten Bereiche, ohne nie Vergebbares", () => {
    expect(applyAreas([], AREAS, new Set(["files", "web", "delegate"]), NEVER).sort())
      .toEqual(["file_read", "file_write", "web_search"])
  })
  it("Einträge außerhalb der Bereiche bleiben erhalten (kategorie:x, Unzugeordnetes)", () => {
    const out = applyAreas(["kategorie:media", "lose_tool", "file_read"], AREAS, new Set(["web"]), NEVER)
    expect(out).toContain("kategorie:media")
    expect(out).toContain("lose_tool")
    expect(out).toContain("web_search")
    expect(out).not.toContain("file_read")                         // Bereich ausgeschaltet → seine Tools verschwinden
  })
  it("nie ein Bereichsname im Ergebnis, keine Dopplungen", () => {
    const out = applyAreas(["file_read"], AREAS, new Set(["files"]), NEVER)
    expect(out.some((i) => i.startsWith("bereich") || i === "files")).toBe(false)
    expect(new Set(out).size).toBe(out.length)
  })
})

describe("toggleArea (der Weg vom Schalter bis zur gespeicherten Liste)", () => {
  const catalog = { groups: [], areas: AREAS, unassigned: [], never: NEVER, neverAreas: new Set(["delegate"]) }
  it("Einschalten fügt die Tool-Namen des Bereichs hinzu", () => {
    expect(toggleArea(["lose_tool"], catalog, "files", true).sort()).toEqual(["file_read", "file_write", "lose_tool"])
  })
  it("Ausschalten entfernt nur die Tools dieses Bereichs; andere Bereiche bleiben an", () => {
    const start = ["file_read", "file_write", "web_search"]
    expect(toggleArea(start, catalog, "files", false)).toEqual(["web_search"])
  })
  it("ein nie vergebbarer Bereich lässt sich nicht einschalten", () => {
    expect(toggleArea([], catalog, "delegate", true)).toEqual([])
  })
})
