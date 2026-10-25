import i18next from "i18next"
import { renderToStaticMarkup } from "react-dom/server"
import { I18nextProvider, initReactI18next } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn() } }))

const de = (await import("@/i18n/locales/de/butler.json")).default
const en = (await import("@/i18n/locales/en/butler.json")).default
const { moduleDefaults, moduleSummary, paletteGroupsFor, cleanSchemaValue } = await import("./moduleNodes")
const { SchemaForm } = await import("./properties/SchemaForm")
const { NodePaletteView } = await import("./NodePalette")
import type { ModuleNode } from "./moduleNodes"

const inst = i18next.createInstance()
beforeAll(async () => {
  await inst.use(initReactI18next).init({
    lng: "de", fallbackLng: "de", ns: ["butler"], defaultNS: "butler",
    resources: { de: { butler: de }, en: { butler: en } }, interpolation: { escapeValue: false },
  })
})
const html = (el: React.ReactElement) => renderToStaticMarkup(<I18nextProvider i18n={inst}>{el}</I18nextProvider>)

const TRIG: ModuleNode = {
  type: "trigger", subtype: "telephony_call_incoming", module: "telephony", label: "Anruf kommt rein",
  description: "Feuert beim Klingeln.", implemented: true,
  params: [{ key: "numbers", label: "Nur diese Nummern", kind: "list_text", required: false, options: [],
    placeholder: "030 1234567", default: null }],
}
const COND: ModuleNode = {
  type: "condition", subtype: "telephony_caller", module: "telephony", label: "Anrufer-Nummer", description: "",
  implemented: true, params: [
    { key: "mode", label: "Art", kind: "select", required: true, options: ["starts", "anonymous"], placeholder: null, default: "starts" },
    { key: "prefix", label: "Beginnt mit", kind: "text", required: false, options: [], placeholder: "030", default: null },
    { key: "seconds", label: "Sekunden", kind: "number", required: false, options: [], placeholder: null, default: 3 },
    { key: "strict", label: "Streng", kind: "checkbox", required: false, options: [], placeholder: null, default: true },
    { key: "note", label: "Notiz", kind: "textarea", required: false, options: [], placeholder: null, default: null },
    { key: "at", label: "Uhrzeit", kind: "time", required: false, options: [], placeholder: null, default: null },
  ],
}
const ACT_SOON: ModuleNode = { ...TRIG, type: "action", subtype: "telephony_soon", label: "Bald", implemented: false, params: [] }

describe("Logik Modul-Bausteine", () => {
  it("Vorgaben aus dem Schema, ohne leere", () => {
    expect(moduleDefaults(COND)).toEqual({ mode: "starts", seconds: 3, strict: true })
    expect(moduleDefaults(TRIG)).toEqual({})
  })
  it("Palette-Gruppen nur, wenn es Modul-Bausteine gibt; je Art sortiert", () => {
    expect(paletteGroupsFor([])).toEqual([])
    const g = paletteGroupsFor([ACT_SOON, COND, TRIG])
    expect(g.map((x) => x.type)).toEqual(["triggerNode", "conditionNode", "actionNode"])
    expect(g[0].items[0]).toMatchObject({ subtype: "telephony_call_incoming", label: "Anruf kommt rein", module: "telephony" })
  })
  it("Vorschau: erste gesetzte Werte, Listen zusammengefasst", () => {
    expect(moduleSummary(TRIG, { numbers: ["030 1234567", "0151 2345678"] })).toBe("030 1234567, 0151 2345678")
    expect(moduleSummary(COND, { mode: "starts", prefix: "030", seconds: 3 })).toBe("starts · 030")
    expect(moduleSummary(COND, {})).toBe("")
  })
  it("Werte säubern: Zahl, Liste, Auswahl nur aus Optionen", () => {
    const p = COND.params
    expect(cleanSchemaValue(p[2], "12")).toBe(12)
    expect(cleanSchemaValue(p[2], "abc")).toBeUndefined()
    expect(cleanSchemaValue(p[0], "anonymous")).toBe("anonymous")
    expect(cleanSchemaValue(p[0], "boese")).toBeUndefined()
    expect(cleanSchemaValue(TRIG.params[0], "030 1\n\n 0151 2 \n")).toEqual(["030 1", "0151 2"])
    expect(cleanSchemaValue(p[3], true)).toBe(true)
  })
})

describe("Formular aus dem Schema", () => {
  it("baut je Feldart das passende Feld", () => {
    const h = html(<SchemaForm node={COND} params={{ mode: "starts", seconds: 3, strict: true }} onChange={() => undefined} />)
    expect(h).toContain("<select")
    expect(h).toContain('value="anonymous"')
    expect(h).toContain('type="number"')
    expect(h).toContain('type="checkbox"')
    expect(h).toContain("<textarea")
    expect(h).toContain('type="time"')
    expect(h).toContain('placeholder="030"')
    expect(h).toContain("Art *")
  })
  it("Liste als mehrzeiliges Feld mit einem Wert je Zeile", () => {
    const h = html(<SchemaForm node={TRIG} params={{ numbers: ["030 1", "0151 2"] }} onChange={() => undefined} />)
    expect(h).toContain("030 1\n0151 2")
    expect(h).toContain("Eine Angabe pro Zeile")
  })
  it("zeigt Beschreibung und Modul", () => {
    const h = html(<SchemaForm node={TRIG} params={{}} onChange={() => undefined} />)
    expect(h).toContain("Feuert beim Klingeln.")
    expect(h).toContain("telephony")
  })
})

describe("Palette", () => {
  it("Gruppe „Module“ mit den Bausteinen, ziehbar; „bald“ nicht ziehbar", () => {
    const h = html(<NodePaletteView moduleNodes={[TRIG, ACT_SOON]} />)
    expect(h).toContain("Module")
    expect(h).toContain("Anruf kommt rein")
    expect(h).toMatch(/data-butler-module-node="telephony_call_incoming"[^>]*draggable="true"|draggable="true"[^>]*data-butler-module-node="telephony_call_incoming"/)
    expect(h).toMatch(/data-butler-module-node="telephony_soon"[^>]*draggable="false"|draggable="false"[^>]*data-butler-module-node="telephony_soon"/)
  })
  it("ohne Modul-Bausteine keine Gruppe – Palette wie bisher", () => {
    const h = html(<NodePaletteView moduleNodes={[]} />)
    expect(h).not.toContain("data-butler-module-node")
    expect(h).not.toContain("data-butler-module-group")
    expect(h).toContain("Trigger")
  })
})
