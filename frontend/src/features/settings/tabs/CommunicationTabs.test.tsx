// Plan docs/plans/meine-einstellungen.md, Task 6: Mail-Hinweis passt zur Rolle.
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

const st = vi.hoisted(() => ({ role: "user" }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: (sel: (s: { role: string }) => unknown) => sel({ role: st.role }) }))
vi.mock("@/features/communication/DiscordCard", () => ({ DiscordCard: () => null }))
vi.mock("@/features/communication/WhatsAppCard", () => ({ WhatsAppCard: () => null }))
import { CommMail } from "./CommunicationTabs"

const render = (role: string) => { st.role = role; return renderToStaticMarkup(<MemoryRouter><CommMail /></MemoryRouter>) }

describe("Kommunikation → Mail", () => {
  it("Nutzer: Hinweis auf den Admin, kein Link ins Admin-Cockpit", () => {
    const html = render("user")
    expect(html).toContain("Admin")
    expect(html).not.toContain("href=")
  })
  it("Admin: Link zu den globalen Settings im Admin-Cockpit, nicht mehr auf /settings", () => {
    const html = render("admin")
    expect(html).toContain('href="/admin?section=system-settings"')
    expect(html).not.toContain('href="/settings"')
  })
})
