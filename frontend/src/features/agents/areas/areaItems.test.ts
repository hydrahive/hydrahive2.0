// Agenten-Bereiche, Aufgabe 7 (AB8): Bereichs-Schalter ↔ Tool-Namen. Gespeichert werden Tool-Namen, nie „kategorie:x“ oder Bereichs-IDs.
import { describe, expect, it } from "vitest"
import { areaIsOn, areaState, toggleArea, wouldEmpty } from "./areaItems"
import type { AreaInfo } from "./areasApi"

const area = (id: string, tools: string[]): AreaInfo =>
  ({ id, group: "g", name: id, sentence: "", marks: [], tools })
const AREAS = [area("files", ["file_read", "file_write"]), area("web", ["web_search", "ssh_exec"]), area("delegate", ["ask_agent"])]
const NEVER = new Set(["ssh_exec", "ask_agent"])
const catalog = { groups: [], areas: AREAS, unassigned: [], unassignedDetails: [], never: NEVER, neverAreas: new Set(["delegate"]) }

describe("areaState / areaIsOn", () => {
  it("an, teilweise, aus", () => {
    expect(areaState(AREAS[0], new Set(["file_read", "file_write"]), NEVER)).toBe("on")
    expect(areaState(AREAS[0], new Set(["file_read"]), NEVER)).toBe("partial")
    expect(areaState(AREAS[0], new Set([]), NEVER)).toBe("off")
  })
  it("ein einzeln abgelehntes Tool hindert den Schalter nicht", () => {
    expect(areaIsOn(AREAS[1], new Set(["web_search"]), NEVER)).toBe(true)
  })
  it("ein Bereich ohne vergebbares Tool ist nie an", () => {
    expect(areaIsOn(AREAS[2], new Set(["ask_agent"]), NEVER)).toBe(false)
  })
})

describe("toggleArea (der Weg vom Schalter bis zur gespeicherten Liste)", () => {
  it("Einschalten fügt die vergebbaren Tool-Namen des Bereichs hinzu", () => {
    expect(toggleArea(["lose_tool"], catalog, "web", true)).toEqual(["lose_tool", "web_search"])
  })
  it("Ausschalten entfernt nur die Tools dieses Bereichs", () => {
    expect(toggleArea(["file_read", "file_write", "web_search"], catalog, "files", false)).toEqual(["web_search"])
  })
  it("ein nie vergebbarer Bereich lässt sich nicht einschalten", () => {
    expect(toggleArea([], catalog, "delegate", true)).toEqual([])
  })
  it("kategorie:x und Unzugeordnetes bleiben erhalten, nie ein Bereichsname im Ergebnis", () => {
    const out = toggleArea(["kategorie:media", "lose_tool"], catalog, "files", true)
    expect(out).toEqual(["kategorie:media", "lose_tool", "file_read", "file_write"])
  })
  it("Review #795 (muss): ein teilweise belegter Bereich bleibt beim Umlegen eines ANDEREN Schalters erhalten", () => {
    expect(toggleArea(["file_read"], catalog, "web", true)).toEqual(["file_read", "web_search"])
    expect(toggleArea(["file_read", "web_search"], catalog, "web", false)).toEqual(["file_read"])
  })
  it("Review #795 (muss): ein- und wieder ausschalten eines anderen Bereichs leert einen Projekt-Pool nie", () => {
    const start = ["web_search", "web_neu_aus_modul_update"]
    const an = toggleArea(start, catalog, "files", true)
    const aus = toggleArea(an, catalog, "files", false)
    expect(aus).toEqual(start)
    expect(wouldEmpty(start, aus)).toBe(false)
  })
})
