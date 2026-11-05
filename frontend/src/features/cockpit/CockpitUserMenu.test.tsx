import { renderToStaticMarkup } from "react-dom/server"
import { afterEach, describe, expect, it, vi } from "vitest"

const auth = vi.hoisted(() => ({
  username: null as string | null,
  role: null as string | null,
  logout: vi.fn(),
}))

vi.mock("@/features/auth/useAuthStore", () => ({
  useAuthStore: <T,>(selector: (state: typeof auth) => T) => selector(auth),
}))

import { CockpitUserMenu } from "./CockpitUserMenu"

afterEach(() => {
  vi.unstubAllGlobals()
  auth.username = null
  auth.role = null
  auth.logout.mockReset()
})

const renderMenu = () => renderToStaticMarkup(<CockpitUserMenu />)

describe("CockpitUserMenu", () => {
  it("zeigt bei normalen Nutzern Benutzername, Rolle und Browserinstanz im geschlossenen Schalter", () => {
    vi.stubGlobal("window", { location: { host: "ws.local" } })
    auth.username = "mira"
    auth.role = "user"

    const html = renderMenu()

    expect(html).toContain("mira")
    expect(html).toContain("NUTZER · ws.local")
    expect(html).toContain('aria-label="Benutzermenü: mira, Nutzer, Instanz ws.local"')
  })

  it("zeigt till mit Admin-Rechten ohne Systemkonto-Warnung", () => {
    vi.stubGlobal("window", { location: { host: "ws.local" } })
    auth.username = "till"
    auth.role = "admin"

    const html = renderMenu()

    expect(html).toContain("ADMIN · ws.local")
    expect(html).toContain("Administrator")
    expect(html).toContain('data-instance-identity="administrator"')
    expect(html).not.toContain("SYSTEM-ADMIN")
    expect(html).not.toContain("Chats und Sitzungen werden getrennt")
    expect(html).not.toContain("border-amber-500")
    expect(html).not.toContain("text-amber-300")
  })

  it("markiert admin mit Shield, Warnstil und Systemadministrator-Beschriftung", () => {
    vi.stubGlobal("window", { location: { host: "ws.local" } })
    auth.username = "admin"
    auth.role = "admin"

    const html = renderMenu()

    expect(html).toContain("ADMIN · ws.local")
    expect(html).toContain("SYSTEM-ADMIN")
    expect(html).toContain('data-instance-identity="system-admin"')
    expect(html).toContain("text-amber-300")
    expect(html).toContain("shield")
  })

  it("rendert nach einem Storewechsel die neue sichtbare Identität", () => {
    vi.stubGlobal("window", { location: { host: "ws.local" } })
    auth.username = "mira"
    auth.role = "user"
    const normal = renderMenu()

    auth.username = "admin"
    auth.role = "admin"
    const admin = renderMenu()

    expect(normal).toContain("NUTZER · ws.local")
    expect(admin).toContain("ADMIN · ws.local")
    expect(admin).not.toContain("mira")
  })
})
