// Plan docs/plans/meine-einstellungen.md, Task 5: „Einstellungen“ führt ins Admin-Fenster Zahnfee.
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/i18n/HelpButton", () => ({ HelpButton: () => null }))
vi.mock("./api", () => ({ zahnfeeApi: { briefing: () => new Promise(() => {}), run: () => new Promise(() => {}) } }))
import { ZahnfeePage } from "./ZahnfeePage"

describe("Zahnfee-Seite", () => {
  it("Link „Einstellungen“ zeigt ins Admin-Fenster, nicht mehr auf /settings", () => {
    const html = renderToStaticMarkup(<MemoryRouter><ZahnfeePage /></MemoryRouter>)
    expect(html).toMatch(/href="\/admin\?section=zahnfee"[^>]*>[\s\S]*?config\.title/)
    expect(html).not.toContain('href="/settings"')
  })
})
