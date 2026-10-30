// Plan docs/plans/admin-reiter-system.md, Task 2: Bereiche je Reiter, Nicht-Admins ohne leere Reiter.
import { renderToStaticMarkup } from "react-dom/server"
import type { ReactNode } from "react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

// vi.mock wird nach oben gezogen: gemeinsame Werte deshalb über vi.hoisted.
const h = vi.hoisted(() => ({ rolle: "admin", teil: (name: string) => () => <div data-part={name} /> }))
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: (sel: (s: { role: string }) => unknown) => sel({ role: h.rolle }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), put: vi.fn(), post: vi.fn() } }))
vi.mock("@/shared/useRestart", () => ({ useRestart: () => ({ state: "idle", open: () => {} }) }))
vi.mock("./AdminOverlay", () => ({ AdminOverlay: ({ children }: { children: ReactNode }) => <div>{children}</div> }))
vi.mock("@/features/system/AgentLinkCard", () => ({ AgentLinkCard: h.teil("agentlink") }))
vi.mock("@/features/system/TailscaleCard", () => ({ TailscaleCard: h.teil("tailscale") }))
vi.mock("@/features/system/BridgeCard", () => ({ BridgeCard: h.teil("bridge") }))
vi.mock("@/features/system/SambaCard", () => ({ SambaCard: h.teil("samba") }))
vi.mock("@/features/system/AddonsCard", () => ({ AddonsCard: h.teil("addons") }))
vi.mock("@/features/system/LocalMediaCard", () => ({ LocalMediaCard: h.teil("media") }))
vi.mock("@/features/system/BackupCard", () => ({ BackupCard: h.teil("backup") }))
vi.mock("@/features/system/MigrationCard", () => ({ MigrationCard: h.teil("migration") }))
vi.mock("@/features/system/HealthBar", () => ({ HealthBar: h.teil("health") }))
import { SystemOverlay } from "./SystemOverlay"

const render = (url: string, role = "admin") => {
  h.rolle = role
  return renderToStaticMarkup(<MemoryRouter initialEntries={[url]}><SystemOverlay onClose={() => {}} /></MemoryRouter>)
}
const teile = (h: string) => [...h.matchAll(/data-part="([a-z]+)"/g)].map((m) => m[1])

describe("Admin-Fenster System", () => {
  it("Überblick ohne Angabe", () => {
    expect(teile(render("/admin?section=system"))).toEqual(["health"])
  })
  it("Netzwerk, Erweiterungen, Sicherung zeigen je ihre Bereiche", () => {
    expect(teile(render("/admin?section=system&tab=netzwerk"))).toEqual(["agentlink", "tailscale", "bridge", "samba"])
    expect(teile(render("/admin?section=system&tab=erweiterungen"))).toEqual(["addons", "media"])
    expect(teile(render("/admin?section=system&tab=sicherung"))).toEqual(["backup", "migration"])
  })
  it("Nicht-Admin: zwei Reiter, Netzwerk nur AgentLink, Admin-Reiter in der Adresse → Überblick", () => {
    expect(render("/admin?section=system", "user").match(/role="tab"/g)).toHaveLength(2)
    expect(teile(render("/admin?section=system&tab=netzwerk", "user"))).toEqual(["agentlink"])
    expect(teile(render("/admin?section=system&tab=sicherung", "user"))).toEqual(["health"])
  })
})
