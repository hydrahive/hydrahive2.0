import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/features/helpdesk/helpApi", () => ({ requestHelpToggle: vi.fn() }))
import { AppFooter } from "./AppFooter"

// docs/specs/plugin-updates.md: Plugin-Zähler in der Fußzeile wie der Modul-Zähler (nur Admin).
const render = (p: Partial<Parameters<typeof AppFooter>[0]> = {}) => renderToStaticMarkup(
  <MemoryRouter>
    <AppFooter version="2.0.0" commit="abc" updateBehind={0} moduleUpdateCount={0} pluginUpdateCount={0}
      isAdmin onUpdateClick={() => {}} {...p} />
  </MemoryRouter>,
).replace(/&quot;/g, '"')

describe("AppFooter – Plugin-Updates", () => {
  it("zeigt den Plugin-Zähler für Admins", () => {
    const html = render({ pluginUpdateCount: 2 })
    expect(html).toContain('update.plugins:{"count":2}')
  })
  it("kein Plugin-Zähler bei 0 oder für Nicht-Admins", () => {
    expect(render({ pluginUpdateCount: 0 })).not.toContain("update.plugins")
    expect(render({ pluginUpdateCount: 3, isAdmin: false })).not.toContain("update.plugins")
  })
  it("Modul-Zähler bleibt unverändert", () => {
    expect(render({ moduleUpdateCount: 1 })).toContain('update.modules:{"count":1}')
  })
})

// docs/specs/chat-mobile-compact.md: Auf dem Handy öffnet ein „?“ in der Fußzeile den Hilfe-Assistenten.
describe("AppFooter – Hilfe-Knopf auf dem Handy", () => {
  const helpButton = (html: string) => html.match(/<button[^>]*data-help-footer="1"[^>]*>/)?.[0] ?? ""
  it("zeigt einen Hilfe-Knopf, nur unter sm sichtbar, mit Beschriftung für Vorlesehilfen", () => {
    const btn = helpButton(render())
    expect(btn).not.toBe("")
    expect(btn).toMatch(/class="[^"]*\bsm:hidden\b/)
    expect(btn).toContain('aria-label="helpdesk_open"')
    expect(btn).toContain('type="button"')
  })
  it("auch für Nicht-Admins", () => {
    expect(helpButton(render({ isAdmin: false }))).not.toBe("")
  })
})

// Plan docs/plans/meine-einstellungen.md, Task 4: Modul-Updates führen direkt ins Admin-Fenster (nicht über den alten Hub).
import { UPDATE_TARGETS } from "./updateTargets"
describe("AppFooter – Ziele der Update-Hinweise", () => {
  it("Module und Plugins öffnen das jeweilige Admin-Fenster", () => {
    expect(UPDATE_TARGETS).toEqual({ modules: "/admin?section=modules", plugins: "/admin?section=plugins" })
  })
})
