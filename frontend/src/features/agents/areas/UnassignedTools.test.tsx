// Agenten-Bereiche, Aufgabe 7 (AB8): Werkzeuge ohne Bereich – nur Liste und Hinweis, keine Zuordnung per Klick (Spec 4.7).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o?.module ? `${k}:${o.module}` : k) }) }))
import { UnassignedTools } from "./UnassignedTools"
import { AreaSwitchList } from "./AreaSwitchList"

describe("UnassignedTools – Modul und Beschreibung, Tool-Namen nur Experte (Review #795)", () => {
  const tools = [{ name: "lose_eins", module: "probe", description: "Macht eins" }, { name: "lose_zwei", module: "probe", description: "" }]
  it("gruppiert nach Modul, zeigt Beschreibungen und den Hinweis – ohne Tool-Namen", () => {
    const html = renderToStaticMarkup(<UnassignedTools tools={tools} />)
    expect(html).toContain("areas.unassigned_module:probe")
    expect(html).toContain("Macht eins")
    expect(html).toContain("areas.unassigned_no_description")
    expect(html).toContain("areas.unassigned_hint")
    expect(html).not.toContain("lose_eins")
    expect(html).not.toContain("<button")                           // keine Zuordnung per Klick
  })
  it("in der Expertenansicht stehen die Tool-Namen dabei", () => {
    expect(renderToStaticMarkup(<UnassignedTools tools={tools} expert />)).toContain("lose_eins")
  })
  it("ohne lose Tools steht eine Entwarnung da", () => {
    expect(renderToStaticMarkup(<UnassignedTools tools={[]} />)).toContain("areas.unassigned_none")
  })
})

describe("AreaSwitchList", () => {
  const catalog = {
    groups: [{ id: "g", name: "Gruppe" }],
    areas: [{ id: "files", group: "g", name: "Dateien", sentence: "Liest Dateien", marks: [], tools: ["file_read"] },
      { id: "delegate", group: "g", name: "Delegieren", sentence: "x", marks: [], tools: ["ask_agent"] }],
    unassigned: [], unassignedDetails: [], never: new Set(["ask_agent"]), neverAreas: new Set(["delegate"]),
  }
  it("nie vergebbare Bereiche sind ausgegraut, abgeschaltet und mit Begründung; Tool-Namen stehen nirgends", () => {
    const html = renderToStaticMarkup(<AreaSwitchList catalog={catalog} items={new Set(["file_read"])} onToggle={() => {}} />)
    expect(html).toContain("areas.never")
    expect(html).toContain("opacity-50")
    expect(html.match(/disabled=""/g)?.length).toBe(1)                 // genau der eine nie-vergebbare Schalter
    expect(html).not.toContain("ask_agent")
    expect(html).not.toContain("file_read")
  })
  it("teilweise belegter Bereich zeigt den Teilweise-Hinweis (Review #795)", () => {
    const c = { ...catalog, areas: [{ ...catalog.areas[0], tools: ["file_read", "read_document"] }, catalog.areas[1]] }
    const html = renderToStaticMarkup(<AreaSwitchList catalog={c} items={new Set(["file_read"])} onToggle={() => {}} />)
    expect(html).toContain("areas.pool_partial")
    expect(html).toContain('data-state="partial"')
  })
})
