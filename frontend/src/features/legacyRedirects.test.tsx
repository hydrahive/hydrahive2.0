// Plan docs/plans/alte-seiten-umleiten.md: /modules und /federation haben nur noch ein Zuhause – das Admin-Fenster.
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

const h = vi.hoisted(() => ({ rolle: "admin" }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: (sel: (s: { role: string }) => unknown) => sel({ role: h.rolle }) }))
// <Navigate> springt erst nach dem Zeichnen (useEffect) – beim statischen Rendern das Sprungziel direkt ausgeben.
vi.mock("react-router-dom", async (orig) => ({
  ...(await orig<typeof import("react-router-dom")>()),
  Navigate: ({ to }: { to: string }) => <p data-ziel={to} />,
}))
vi.mock("@/features/cockpit/admin/FederationOverlay", () => ({ FederationOverlay: () => <div data-part="federation-overlay" /> }))
import { ModulesPage } from "./modules/ModulesPage"
import { FederationPage } from "./federation/FederationPage"

const render = (url: string, role = "admin") => {
  h.rolle = role
  return renderToStaticMarkup(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/modules" element={<ModulesPage />} />
        <Route path="/federation" element={<FederationPage />} />
      </Routes>
    </MemoryRouter>,
  )
}
const ziel = (out: string) => out.match(/data-ziel="([^"]*)"/)?.[1]?.replace(/&amp;/g, "&")

describe("Alte Seiten leiten ins Admin-Fenster", () => {
  it("/modules → Module-Fenster, Reiter wird mitgenommen", () => {
    expect(ziel(render("/modules"))).toBe("/admin?section=modules")
    expect(ziel(render("/modules?tab=verfuegbar"))).toBe("/admin?section=modules&tab=verfuegbar")
  })
  it("/federation als Admin → Föderations-Fenster, Reiter wird mitgenommen", () => {
    expect(ziel(render("/federation"))).toBe("/admin?section=federation")
    expect(ziel(render("/federation?tab=peers"))).toBe("/admin?section=federation&tab=peers")
  })
  it("/federation als freigegebener Nutzer: dasselbe Fenster hier, keine Umleitung ins Admin-Cockpit", () => {
    const out = render("/federation", "user")
    expect(ziel(out)).toBeUndefined()
    expect(out).toContain('data-part="federation-overlay"')
  })
})
