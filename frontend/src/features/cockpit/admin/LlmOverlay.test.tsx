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
import { LlmOverlay } from "./LlmOverlay"

describe("Admin-Fenster KI-Modelle", () => {
  it("enthält den Abschnitt Bild-/Video-Dienste nach den Standard-Modellen", () => {
    const html = renderToStaticMarkup(<LlmOverlay onClose={() => {}} />)
    expect(html).toContain('data-testid="media-backends"')
    expect(html.indexOf("default-models")).toBeLessThan(html.indexOf("media-backends"))
  })
})
