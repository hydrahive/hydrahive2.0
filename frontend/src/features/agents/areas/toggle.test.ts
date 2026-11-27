import { describe, expect, it } from "vitest"
import { toggle } from "./toggle"

// Spiegel von agents/area_state.py::toggle – dieselben Fälle wie test_toggle_* im Backend (identische Ergebnisse).
const FILES_WRITE = ["file_patch", "file_write"]

describe("toggle – TS-Spiegel von area_state.toggle", () => {
  it("an/aus nur eigene Tools, Reihenfolge stabil, Eingabe unverändert", () => {
    const start = ["web_search", "file_read"]
    const an = toggle(start, FILES_WRITE, true)
    expect(an).toEqual(["web_search", "file_read", "file_patch", "file_write"])
    expect(toggle(an, FILES_WRITE, false)).toEqual(start)
    expect(toggle(start, FILES_WRITE, false)).toEqual(start)
    expect(toggle(an, FILES_WRITE, true)).toEqual(an)                  // idempotent, keine Dubletten
    expect(start).toEqual(["web_search", "file_read"])
  })
  it("lässt fremde Tools stehen: plugin__, mcp__, Altbestand, kategorie:x", () => {
    const start = ["plugin__x__y", "mcp__a__b", "altlast_tool", "file_write", "kategorie:memory"]
    expect(toggle(start, FILES_WRITE, false)).toEqual(["plugin__x__y", "mcp__a__b", "altlast_tool", "kategorie:memory"])
    const an = toggle(start, ["file_read", "read_document"], true)
    for (const keep of ["plugin__x__y", "mcp__a__b", "altlast_tool", "kategorie:memory"]) expect(an).toContain(keep)
  })
  it("lässt die Grundausstattung stehen", () => {
    const start = ["find_tools", "run_tool", "todo_write", "list_skills", "file_write"]
    expect(toggle(start, FILES_WRITE, false)).toEqual(["find_tools", "run_tool", "todo_write", "list_skills"])
    expect(toggle(["find_tools"], FILES_WRITE, true)[0]).toBe("find_tools")
  })
  it("schreibt nie bereich:x", () => {
    expect(toggle([], FILES_WRITE, true).some((t) => t.startsWith("bereich") || t.startsWith("area"))).toBe(false)
  })
})
