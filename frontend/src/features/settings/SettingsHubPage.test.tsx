// Plan docs/plans/meine-einstellungen.md, Task 3: alte Admin-Adressen leiten um, sonst „Meine Einstellungen“.
import { renderToStaticMarkup } from "react-dom/server"
import type { ReactNode } from "react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

// Statisches Rendern führt <Navigate> nicht aus → Ziel als Marker sichtbar machen.
vi.mock("react-router-dom", async (orig) => ({
  ...(await orig<typeof import("react-router-dom")>()),
  Navigate: ({ to }: { to: string }) => <div data-at={to} />,
}))
vi.mock("react", async (orig) => ({ ...(await orig<typeof import("react")>()), lazy: () => () => null }))
vi.mock("@/features/cockpit/CockpitShell", () => ({ CockpitShell: ({ children }: { children: ReactNode }) => <div>{children}</div> }))
vi.mock("@/features/cockpit/CockpitTopbar", () => ({ CockpitTopbar: () => null }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: (sel: (s: { role: string }) => unknown) => sel({ role: "admin" }) }))
vi.mock("./ContentArea", () => ({ ContentArea: ({ group }: { group: { id: string } }) => <div data-group={group.id} /> }))
vi.mock("./SubMenu", () => ({ SubMenu: () => null }))
import { SettingsHubPage } from "./SettingsHubPage"

const render = (url: string) => renderToStaticMarkup(
  <MemoryRouter initialEntries={[url]}>
    <Routes>
      <Route path="/settings" element={<SettingsHubPage />} />
      <Route path="/settings/:groupId" element={<SettingsHubPage />} />
    </Routes>
  </MemoryRouter>,
)

describe("Meine Einstellungen", () => {
  it("alte Adresse einer Admin-Gruppe landet im Admin-Fenster", () => {
    expect(render("/settings/modules")).toContain('data-at="/admin?section=modules"')
    expect(render("/settings/connections")).toContain('data-at="/admin?section=system"')
    expect(render("/settings/zahnfee")).toContain('data-at="/admin?section=zahnfee"')
  })
  it("persönliche Gruppe bleibt hier, Kopf heißt „Meine Einstellungen“", () => {
    const html = render("/settings/credentials")
    expect(html).toContain('data-group="credentials"')
    expect(html).toContain("Meine Einstellungen")
    expect(html).not.toContain("data-at=")
  })
  it("unbekannte Gruppe: erste Gruppe, keine Umleitung", () => {
    expect(render("/settings/xyz")).toContain('data-group="agents"')
  })
  it("Liste links zeigt keine Admin-Gruppen mehr", () => {
    const html = render("/settings")
    for (const label of ["Module", "Plugins", "KI-Modelle", "Benutzer", "Globale Settings", "Föderation"]) {
      expect(html).not.toContain(`<span class="truncate">${label}</span>`)
    }
    expect(html).toContain('<span class="truncate">Zugangsdaten</span>')
  })
})
