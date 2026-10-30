// Plan docs/plans/admin-reiter-benutzer.md: Reiter Benutzer, Gruppen, API-Keys.
import { renderToStaticMarkup } from "react-dom/server"
import type { ReactNode } from "react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import { parseUsersTab, USERS_TABS } from "./usersTabs"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), put: vi.fn(), post: vi.fn(), del: vi.fn() } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: (sel: (s: { username: string }) => unknown) => sel({ username: "admin" }) }))
vi.mock("@/i18n/HelpButton", () => ({ HelpButton: () => null }))
vi.mock("./AdminOverlay", () => ({
  AdminOverlay: ({ children, headerActions }: { children: ReactNode; headerActions?: ReactNode }) =>
    <div><header>{headerActions}</header>{children}</div>,
}))
vi.mock("@/features/access/GroupsSection", () => ({ GroupsSection: () => <div data-part="gruppen" /> }))
vi.mock("@/features/users/ApiKeysSection", () => ({ ApiKeysSection: () => <div data-part="api-keys" /> }))
vi.mock("./UserRows", () => ({ UserRows: () => <div data-part="benutzer" /> }))
import { UsersOverlay } from "./UsersOverlay"

const render = (url: string) =>
  renderToStaticMarkup(<MemoryRouter initialEntries={[url]}><UsersOverlay onClose={() => {}} /></MemoryRouter>)
const teile = (h: string) => [...h.matchAll(/data-part="([a-z-]+)"/g)].map((m) => m[1])
const kopf = (h: string) => h.match(/<header>([\s\S]*?)<\/header>/)?.[1] ?? ""

describe("Benutzer-Reiter", () => {
  it("drei Reiter, Rückfall auf Benutzer", () => {
    expect(USERS_TABS).toEqual(["benutzer", "gruppen", "api-keys"])
    expect(parseUsersTab(null)).toBe("benutzer")
    expect(parseUsersTab("api-keys")).toBe("api-keys")
    expect(parseUsersTab("x")).toBe("benutzer")
  })
})

describe("Admin-Fenster Benutzer", () => {
  it("je Reiter genau sein Teil", () => {
    // Reiter Benutzer: beim ersten Aufbau lädt die Liste noch (Laden passiert im Effekt).
    const benutzer = render("/admin?section=users")
    expect(teile(benutzer)).toEqual([])
    expect(benutzer).toMatch(/role="tabpanel"[\s\S]*Benutzer werden geladen/)
    expect(teile(render("/admin?section=users&tab=gruppen"))).toEqual(["gruppen"])
    expect(teile(render("/admin?section=users&tab=api-keys"))).toEqual(["api-keys"])
  })
  it("„Neuer Benutzer“ nur im Reiter Benutzer", () => {
    expect(kopf(render("/admin?section=users"))).toContain("actions.new")
    expect(kopf(render("/admin?section=users&tab=gruppen"))).not.toContain("actions.new")
    expect(kopf(render("/admin?section=users&tab=api-keys"))).not.toContain("actions.new")
  })
})
