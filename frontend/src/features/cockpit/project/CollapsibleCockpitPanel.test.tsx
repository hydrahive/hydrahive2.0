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
    expect(html).not.toMatch(/bg-gradient-to-b/)
    expect(html).toMatch(/border-left-color:\s*#22d3ee/)
    expect(html).toContain("bg-s-box")
  })
  it("alle fünf Boxen im Projekt-Cockpit haben ein Thema", () => {
    const src = readFileSync(join(__dirname, "..", "ProjectCockpitPage.tsx"), "utf8")
    const boxes = src.match(/<CollapsibleCockpitPanel[\s\S]*?>/g) ?? []
    expect(boxes).toHaveLength(5)
    for (const b of boxes) expect(b).toMatch(/theme="(wissen|werkzeug|status|ideen|kontakt)"/)
  })
  it("Kopf-Knopf auf eigener Stufe, Zustand zeigt Schild", () => {
    const html = renderToStaticMarkup(
      <CollapsibleCockpitPanel title="Git" eyebrow="Git" collapsed={false} onToggle={() => {}} theme="status" status="warnung"><p>x</p></CollapsibleCockpitPanel>,
    )
    expect(html).toMatch(/<button[^>]*bg-s-kopf/)
    expect(html).toContain('data-box-status="warnung"')
    expect(html).toMatch(/border-left-color:\s*#fbbf24/)
    expect(html).not.toMatch(/#151c2b|#2a364b/)
  })
})
