// Plan docs/plans/meine-einstellungen.md (Umleitung) und meine-einstellungen-kompakt.md (Reiter statt Spalten).
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
vi.mock("./ContentArea", () => ({ ContentArea: ({ group }: { group: { id: string; tabs: string[] } }) => <div data-group={group.id} data-inner-tabs={group.tabs.length} /> }))
import { SettingsHubPage } from "./SettingsHubPage"

const render = (url: string) => renderToStaticMarkup(
  <MemoryRouter initialEntries={[url]}>
    <Routes>
      <Route path="/settings" element={<SettingsHubPage />} />
      <Route path="/settings/:groupId" element={<SettingsHubPage />} />
    </Routes>
  </MemoryRouter>,
)
const tabs = (h: string) => [...h.matchAll(/<button[^>]*role="tab"[^>]*>(?:<svg[\s\S]*?<\/svg>)?([^<]*)<\/button>/g)].map((m) => m[1])
const selected = (h: string) => [...h.matchAll(/<button[^>]*role="tab"[^>]*aria-selected="true"[^>]*>(?:<svg[\s\S]*?<\/svg>)?([^<]*)</g)].map((m) => m[1])

describe("Meine Einstellungen: Umleitung", () => {
  it("alte Adresse einer Admin-Gruppe landet im Admin-Fenster", () => {
    expect(render("/settings/modules")).toContain('data-at="/admin?section=modules"')
    expect(render("/settings/connections")).toContain('data-at="/admin?section=system"')
    expect(render("/settings/zahnfee")).toContain('data-at="/admin?section=zahnfee"')
  })
})

describe("Meine Einstellungen: Reiter statt Spalten", () => {
  it("sechs Reiter in fester Reihenfolge, Kopf heißt „Meine Einstellungen“", () => {
    const h = render("/settings")
    expect(tabs(h)).toEqual(["Agenten", "Projekte", "Kommunikation", "Zugangsdaten", "Skills", "Butler"])
    expect(h).toContain("Meine Einstellungen")
  })
  it("Reiter folgt der URL", () => {
    const h = render("/settings/credentials")
    expect(selected(h)).toEqual(["Zugangsdaten"])
    expect(h).toContain('data-group="credentials"')
    expect(h).not.toContain("data-at=")
  })
  it("ohne/unbekannte Gruppe: erster Reiter", () => {
    expect(selected(render("/settings"))).toEqual(["Agenten"])
    expect(selected(render("/settings/xyz"))).toEqual(["Agenten"])
  })
  it("keine Gruppen-Spalte und keine Rechtsspalte mehr", () => {
    const h = render("/settings/agents")
    expect(h).not.toContain("Gruppe wählen")
    expect(h).not.toMatch(/lg:grid-cols-\[220px/)
  })
  it("innere Reiter nur, wo eine Gruppe mehrere Teile hat", () => {
    expect(render("/settings/communication")).toContain('data-inner-tabs="3"')
    expect(render("/settings/credentials")).toContain('data-inner-tabs="0"')
    expect(render("/settings/agents")).toContain('data-inner-tabs="0"')
  })
})
