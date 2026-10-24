import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import { ProjectMobileTabs } from "./ProjectMobileTabs"

const render = (active: "project" | "chat" | "files" = "chat") =>
  renderToStaticMarkup(<ProjectMobileTabs active={active} onChange={() => {}} />)

describe("ProjectMobileTabs", () => {
  it("ist eine Reiterleiste, die ab xl verschwindet", () => {
    const html = render()
    expect(html).toMatch(/<div[^>]*role="tablist"[^>]*>/)
    expect(html).toMatch(/role="tablist"[^>]*class="[^"]*\bxl:hidden\b/)
  })

  it("zeigt drei Reiter mit Texten aus i18n in der Reihenfolge Projekt, Chat, Dateien", () => {
    const html = render()
    const labels = [...html.matchAll(/role="tab"[^>]*>([^<]+)</g)].map((m) => m[1])
    expect(labels).toEqual(["cockpit_tabs.project", "cockpit_tabs.chat", "cockpit_tabs.files"])
  })

  it("markiert genau den aktiven Reiter und verweist auf seinen Bereich", () => {
    const html = render("files")
    const selected = [...html.matchAll(/aria-selected="true"/g)]
    expect(selected).toHaveLength(1)
    expect(html).toMatch(/aria-selected="true"[^>]*aria-controls="project-pane-files"|aria-controls="project-pane-files"[^>]*aria-selected="true"/)
    expect(html).toContain('aria-controls="project-pane-chat"')
    expect(html).toContain('aria-controls="project-pane-project"')
  })

  it("Reiter sind echte Knöpfe (type=button)", () => {
    const html = render()
    expect([...html.matchAll(/<button[^>]*type="button"[^>]*role="tab"|<button[^>]*role="tab"[^>]*type="button"/g)]).toHaveLength(3)
  })
})
