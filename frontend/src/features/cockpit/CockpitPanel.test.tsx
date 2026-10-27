// Plan docs/plans/hydra-box-koepfe.md, Task 3: Boxen mit Thema bekommen Kopf + Verlauf.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { CockpitPanel } from "./CockpitPanel"

describe("CockpitPanel", () => {
  it("ohne Thema: unverändert, kein Bild", () => {
    const html = renderToStaticMarkup(<CockpitPanel title="Status" eyebrow="Admin"><p>x</p></CockpitPanel>)
    expect(html).not.toContain("<img")
    expect(html).toContain("Status")
  })
  it("mit Thema: Kopfbild vor dem Titel, Verlauf in der Themenfarbe", () => {
    const html = renderToStaticMarkup(<CockpitPanel title="Werkzeuge" eyebrow="Kompakt" theme="werkzeug"><p>x</p></CockpitPanel>)
    expect(html).toMatch(/<img[^>]*kopf-3-orange[\s\S]*Werkzeuge/)
    expect(html).toContain("data-box-theme=\"werkzeug\"")
    expect(html).toMatch(/bg-gradient-to-b/)
  })
  it("mit Thema aber ohne Titel: trotzdem Kopf (z. B. reine Inhaltsbox)", () => {
    expect(renderToStaticMarkup(<CockpitPanel theme="status"><p>x</p></CockpitPanel>)).toContain("kopf-4-tuerkis")
  })
})
