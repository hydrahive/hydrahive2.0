// Plan docs/plans/admin-luecken-schliessen.md, Task 6: Föderation im Admin-Cockpit, mit Reitern.
import { renderToStaticMarkup } from "react-dom/server"
import type { ReactNode } from "react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("./AdminOverlay", () => ({ AdminOverlay: ({ children }: { children: ReactNode }) => <div>{children}</div> }))
vi.mock("@/features/federation/WorkstationsPanel", () => ({ WorkstationsPanel: () => <div data-part="workstations" /> }))
vi.mock("@/features/federation/_PeersSection", () => ({ PeersSection: () => <div data-part="peers" /> }))
vi.mock("@/features/federation/_ClientConnectionsSection", () => ({ ClientConnectionsSection: () => <div data-part="clients" /> }))
vi.mock("@/features/federation/_DataminingInstancesSection", () => ({ DataminingInstancesSection: () => <div data-part="datamining" /> }))
import { FederationOverlay } from "./FederationOverlay"

const render = (url: string) =>
  renderToStaticMarkup(<MemoryRouter initialEntries={[url]}><FederationOverlay onClose={() => {}} /></MemoryRouter>)
const parts = (h: string) => [...h.matchAll(/data-part="([a-z]+)"/g)].map((m) => m[1])
const selected = (h: string) => [...h.matchAll(/<button[^>]*role="tab"[^>]*aria-selected="true"[^>]*>([^<]*)</g)].map((m) => m[1])

describe("Admin-Fenster Föderation", () => {
  it("vier Reiter", () => {
    expect(render("/admin?section=federation").match(/role="tab"/g)).toHaveLength(4)
  })
  it("ohne Reiter in der URL: nur Workstations", () => {
    const h = render("/admin?section=federation")
    expect(parts(h)).toEqual(["workstations"])
    expect(selected(h)).toEqual(["tabs.workstations"])
  })
  it("Reiter aus der URL: nur Clients", () => {
    const h = render("/admin?section=federation&tab=clients")
    expect(parts(h)).toEqual(["clients"])
    expect(selected(h)).toEqual(["tabs.clients"])
  })
  it("unbekannter Reiter: Workstations", () => {
    expect(parts(render("/admin?section=federation&tab=xyz"))).toEqual(["workstations"])
  })
})
