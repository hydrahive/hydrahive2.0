import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import { ModuleViewFrame } from "./ModuleViewFrame"

describe("ModuleViewFrame", () => {
  it("zeigt vor dem Sichtbarwerden nur Titel und Platzhalter, keinen iframe", () => {
    const html = renderToStaticMarkup(<ModuleViewFrame module="diagramme" viewId="d1" title="Websuche" />)
    expect(html).toContain("Websuche")
    expect(html).not.toContain("<iframe")
  })

  it("ohne Titel steht ein neutraler Text", () => {
    const html = renderToStaticMarkup(<ModuleViewFrame module="diagramme" viewId="d1" title="" />)
    expect(html).toContain("module_view.untitled")
  })
})
