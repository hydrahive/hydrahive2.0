// Agenten-Bereiche, Aufgabe 7 (AB8): Werkzeuge ohne Bereich – nur Liste und Hinweis, keine Zuordnung per Klick (Spec 4.7).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import { UnassignedTools } from "./UnassignedTools"
import { AreaSwitchList } from "./AreaSwitchList"

describe("UnassignedTools", () => {
  it("zeigt die Tools und den Hinweis, dass das Modul seinen Bereich melden muss", () => {
    const html = renderToStaticMarkup(<UnassignedTools tools={["lose_eins", "lose_zwei"]} />)
    expect(html).toContain("lose_eins")
    expect(html).toContain("lose_zwei")
    expect(html).toContain("areas.unassigned_hint")
    expect(html).not.toContain("<button")                           // keine Zuordnung per Klick
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
    unassigned: [], never: new Set(["ask_agent"]), neverAreas: new Set(["delegate"]),
  }
  it("nie vergebbare Bereiche sind ausgegraut, abgeschaltet und mit Begründung; Tool-Namen stehen nirgends", () => {
    const html = renderToStaticMarkup(<AreaSwitchList catalog={catalog} items={new Set(["file_read"])} onToggle={() => {}} />)
    expect(html).toContain("areas.never")
    expect(html).toContain("opacity-50")
    expect(html.match(/disabled=""/g)?.length).toBe(1)                 // genau der eine nie-vergebbare Schalter
    expect(html).not.toContain("ask_agent")
    expect(html).not.toContain("file_read")
  })
})
