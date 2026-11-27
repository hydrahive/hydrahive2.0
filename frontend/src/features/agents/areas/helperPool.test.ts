import { describe, expect, it } from "vitest"
import { helperPoolItems, neverGiven } from "./helperPool"
import type { Area } from "./types"

const a = (id: string, tools: string[]): Area => ({ id, group: "files_code", name: id, sentence: id, marks: [], tools, source: "core" })
const AREAS = [a("files_read", ["file_read", "read_document"]), a("files_write", ["file_write", "file_patch"]),
  a("shell", ["shell_exec"]), a("delegate", ["ask_agent"]), a("helpers", ["create_specialist", "write_skill"])]
const FORBIDDEN = ["ask_agent", "create_specialist", "write_skill", "run_tool", "find_tools"]

describe("helperPoolItems – AB7", () => {
  it("enthält nur Tool-Namen der eingeschalteten Bereiche, nie kategorie:x", () => {
    const items = helperPoolItems(AREAS, ["files_read", "files_write"], FORBIDDEN)
    expect(items).toEqual(["file_read", "read_document", "file_write", "file_patch"])
    expect(items.some((i) => i.startsWith("kategorie:"))).toBe(false)
  })
  it("enthält nichts aus forbidden, auch wenn der Bereich eingeschaltet ist", () => {
    const items = helperPoolItems(AREAS, ["helpers", "delegate", "files_read"], FORBIDDEN)
    expect(items).toEqual(["file_read", "read_document"])
    for (const f of FORBIDDEN) expect(items).not.toContain(f)
  })
  it("ein gemischter Bereich gibt nur den erlaubten Teil weiter", () => {
    const mixed = [a("mixed", ["file_read", "ask_agent"])]
    expect(helperPoolItems(mixed, ["mixed"], FORBIDDEN)).toEqual(["file_read"])
  })
  it("keine Bereiche an → leerer Pool, Dubletten fallen weg, unbekannte Bereiche werden ignoriert", () => {
    expect(helperPoolItems(AREAS, [], FORBIDDEN)).toEqual([])
    expect(helperPoolItems(AREAS, ["gibt_es_nicht"], FORBIDDEN)).toEqual([])
    const dup = [a("x", ["file_read"]), a("y", ["file_read"])]
    expect(helperPoolItems(dup, ["x", "y"], FORBIDDEN)).toEqual(["file_read"])
  })
})

describe("neverGiven – ausgegraut", () => {
  it("ein Bereich, dessen Tools alle in forbidden liegen, wird nie per Auftrag vergeben", () => {
    expect(neverGiven(AREAS[3], FORBIDDEN)).toBe(true)          // delegate: nur ask_agent
    expect(neverGiven(AREAS[4], FORBIDDEN)).toBe(true)          // helpers: nur Authoring
    expect(neverGiven(AREAS[0], FORBIDDEN)).toBe(false)
  })
  it("ein leerer Bereich gilt als nicht vergebbar", () => {
    expect(neverGiven(a("leer", []), FORBIDDEN)).toBe(true)
  })
  it("ein gemischter Bereich ist nicht ausgegraut", () => {
    expect(neverGiven(a("mixed", ["file_read", "ask_agent"]), FORBIDDEN)).toBe(false)
  })
})

describe("extraPoolItems – fremde Pool-Einträge bleiben erhalten (Review #794)", () => {
  it("liefert kategorie:x und Einzel-Tools, die keinen ganzen Bereich abdecken", async () => {
    const { extraPoolItems } = await import("./helperPool")
    const areas = [
      { id: "files_read", group: "g", name: "", sentence: "", marks: [], tools: ["file_read", "read_document"], source: "core" },
      { id: "web_search", group: "g", name: "", sentence: "", marks: [], tools: ["web_search"], source: "core" },
    ]
    expect(extraPoolItems(areas, ["web_search", "file_read", "kategorie:files"], [])).toEqual(["file_read", "kategorie:files"])
  })
})
