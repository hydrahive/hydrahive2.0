import { describe, expect, it } from "vitest"
import { applyMany, overlay } from "./overlay"
import type { AreaCatalog, AreaState, AreaStatus } from "./types"

const area = (id: string, tools: string[]) => ({ id, group: "files_code", name: id, sentence: "", marks: [], tools, source: "core" })
const catalog: AreaCatalog = {
  groups: [], base: [], unassigned: [],
  areas: [area("files_read", ["file_read", "read_document"]), area("web_search", ["web_search"]), area("mail_write", ["send_mail"])],
  categories: { files: ["file_read", "read_document", "file_write"] },
}
const s = (id: string, extra: Partial<AreaState> = {}): AreaState =>
  ({ id, state: "off", have: [], missing: [], new: [], via_category: [], ...extra })
const status = (areas: AreaState[]): AreaStatus => ({ editable: true, areas })
const st = (r: AreaStatus, id: string) => r.areas.find((a) => a.id === id)!

describe("overlay – Spiegel von area_state.area_states (Review #794)", () => {
  it("on, wenn alle Tools des Bereichs einzeln da sind", () => {
    const r = overlay(catalog, status([s("files_read")]), ["file_read", "read_document"])
    expect(st(r, "files_read").state).toBe("on")
  })
  it("partial nach Entfernen eines Tools, ohne „neu“", () => {
    const r = overlay(catalog, status([s("files_read")]), ["file_read"])
    expect(st(r, "files_read")).toMatchObject({ state: "partial", new: [] })
  })
  it("on mit Hinweis, wenn nur neu registrierte Tools fehlen", () => {
    const r = overlay(catalog, status([s("files_read", { new: ["read_document"] })]), ["file_read"])
    expect(st(r, "files_read")).toMatchObject({ state: "on", new: ["read_document"] })
  })
  it("„neu“ verschwindet, sobald der Bereich nicht mehr an ist", () => {
    const r = overlay(catalog, status([s("files_read", { new: ["read_document"] })]), [])
    expect(st(r, "files_read")).toMatchObject({ state: "off", new: [] })
  })
  it("ausgeschaltet, aber über kategorie:x weiter da → partial, nicht off", () => {
    const r = overlay(catalog, status([s("files_read")]), ["kategorie:files"])
    expect(st(r, "files_read")).toMatchObject({ state: "partial", via_category: ["file_read", "read_document"] })
  })
  it("einzeln + Kategorie: einzeln zählt als have, nicht als via_category", () => {
    const r = overlay(catalog, status([s("files_read")]), ["file_read", "kategorie:files"])
    expect(st(r, "files_read")).toMatchObject({ have: ["file_read"], via_category: ["read_document"], state: "on" })   // wie area_state.py:64
  })
  it("leerer Bereich übernimmt den Server-Stand", () => {
    const c = { ...catalog, areas: [...catalog.areas, area("leer", [])] }
    const r = overlay(c, status([s("leer", { state: "off" })]), ["file_read"])
    expect(st(r, "leer").state).toBe("off")
  })
})

describe("applyMany – mehrere Vorschläge in einem Schritt (Review #794, muss)", () => {
  it("übernimmt ALLE Bereiche, nicht nur den letzten", () => {
    expect(applyMany(["file_read"], catalog, ["web_search", "mail_write"])).toEqual(["file_read", "web_search", "send_mail"])
  })
  it("unbekannte IDs und Dubletten ändern nichts", () => {
    expect(applyMany(["web_search"], catalog, ["gibt_es_nicht", "web_search"])).toEqual(["web_search"])
  })
})
