// Plan docs/plans/meine-einstellungen-kompakt.md, Task 1: Suche im Auswahlfeld.
import { describe, expect, it } from "vitest"
import { filterItems, type PickerItem } from "./pickerFilter"

const items: PickerItem[] = [
  { id: "1", name: "admin's Assistant", detail: "Master · claude-sonnet-4-6" },
  { id: "2", name: "Frontend-Prüfer", detail: "Spezialist · gpt-5" },
  { id: "3", name: "Videoeditor", detail: "Projekt · claude-opus-5" },
]
const ids = (xs: PickerItem[]) => xs.map((x) => x.id)

describe("filterItems", () => {
  it("leere Suche zeigt alle", () => {
    expect(ids(filterItems(items, ""))).toEqual(["1", "2", "3"])
  })
  it("findet auch über den Zusatz (Modell), ohne Rücksicht auf Groß/Klein", () => {
    expect(ids(filterItems(items, "SONNET"))).toEqual(["1"])
  })
  it("findet über den Namen", () => {
    expect(ids(filterItems(items, "prüf"))).toEqual(["2"])
  })
  it("Leerzeichen am Rand zählen nicht", () => {
    expect(ids(filterItems(items, "  admin  "))).toEqual(["1"])
  })
  it("kein Treffer → leer, Reihenfolge bleibt sonst erhalten", () => {
    expect(filterItems(items, "xyz")).toEqual([])
    expect(ids(filterItems(items, "claude"))).toEqual(["1", "3"])
  })
})
