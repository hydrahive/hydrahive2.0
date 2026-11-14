// Plan docs/plans/admin-luecken-schliessen.md, Task 3: Bild-/Video-Dienste auch im Admin-Fenster KI-Modelle.
import { renderToStaticMarkup } from "react-dom/server"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("./AdminOverlay", () => ({ AdminOverlay: ({ children }: { children: ReactNode }) => <div>{children}</div> }))
vi.mock("@/features/llm/AnthropicUsageCard", () => ({ AnthropicUsageCard: () => null }))
vi.mock("@/features/llm/DefaultModelsSection", () => ({ DefaultModelsSection: () => <div data-testid="default-models" /> }))
vi.mock("@/features/llm/MediaBackendsSection", () => ({ MediaBackendsSection: () => <div data-testid="media-backends" /> }))
vi.mock("@/features/llm/api", () => ({ llmApi: { getConfig: () => new Promise(() => {}) } }))
vi.mock("@/features/llm/templates/TemplatesTab", () => ({ TemplatesTab: () => <div data-testid="templates-tab" /> }))
import { MemoryRouter } from "react-router-dom"
import { LlmOverlay } from "./LlmOverlay"

const render = (url = "/admin?section=llm") =>
  renderToStaticMarkup(<MemoryRouter initialEntries={[url]}><LlmOverlay onClose={() => {}} /></MemoryRouter>)

describe("Admin-Fenster KI-Modelle", () => {
  it("enthält den Abschnitt Bild-/Video-Dienste nach den Standard-Modellen", () => {
    const html = render()
    expect(html).toContain('data-testid="media-backends"')
    expect(html.indexOf("default-models")).toBeLessThan(html.indexOf("media-backends"))
  })

  it("hat die Reiter Anbieter und Agenten-Templates, Start auf Anbieter", () => {
    const html = render()
    expect(html).toContain("tabs.providers")
    expect(html).toContain("tabs.templates")
    expect(html).not.toContain('data-testid="templates-tab"')
  })

  it("Link aus einem Hinweis öffnet direkt den Reiter Agenten-Templates", () => {
    expect(render("/admin?section=llm&tab=templates&template=projekt-master")).toContain('data-testid="templates-tab"')
  })
})
