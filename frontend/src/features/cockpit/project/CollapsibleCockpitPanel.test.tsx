// Task 0dda5420: Auch die aufklappbaren Boxen im Projekt-Cockpit bekommen den Hydra-Kopf ihres Themas.
import { renderToStaticMarkup } from "react-dom/server"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { CollapsibleCockpitPanel } from "./CollapsibleCockpitPanel"

const box = (theme?: "status") => renderToStaticMarkup(
  <CollapsibleCockpitPanel title="Git Status" eyebrow="Git" collapsed onToggle={() => {}} theme={theme}><p>x</p></CollapsibleCockpitPanel>,
)

describe("CollapsibleCockpitPanel", () => {
  it("ohne Thema: kein Bild", () => {
    expect(box()).not.toContain("<img")
  })
  it("mit Thema: Kopf vor dem Titel, Verlauf in der Themenfarbe, auch zugeklappt", () => {
    const html = box("status")
    expect(html).toMatch(/<img[^>]*kopf-4-tuerkis[\s\S]*Git Status/)
    expect(html).toContain('data-box-theme="status"')
    expect(html).toMatch(/bg-gradient-to-b/)
  })
  it("alle fünf Boxen im Projekt-Cockpit haben ein Thema", () => {
    const src = readFileSync(join(__dirname, "..", "ProjectCockpitPage.tsx"), "utf8")
    const boxes = src.match(/<CollapsibleCockpitPanel[\s\S]*?>/g) ?? []
    expect(boxes).toHaveLength(5)
    for (const b of boxes) expect(b).toMatch(/theme="(wissen|werkzeug|status|ideen|kontakt)"/)
  })
})
