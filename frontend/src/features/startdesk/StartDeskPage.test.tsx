// docs/specs/startdesktop.md: Startseite – Begrüßung, Suche, Buddy-Knopf, Bereichs-Kacheln.
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import type { LucideIcon } from "lucide-react"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/features/cockpit/CockpitTopbar", () => ({ CockpitTopbar: () => <header data-topbar="1" /> }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: (sel: (s: { username: string }) => unknown) => sel({ username: "till" }) }))
const I = (() => null) as unknown as LucideIcon
vi.mock("./useAreas", async () => {
  const { fillAreas } = await import("./areaLogic")
  const items = ["/storyteller", "/notizbuch", "/studio", "/projects"].map((p) => ({ path: p, icon: I, labelKey: p.slice(1), group: "working" }))
  return { useAreas: () => ({ areas: fillAreas(items, true), label: (i: { labelKey: string }) => i.labelKey }) }
})
vi.mock("./useAreaPrefs", () => ({ useAreaPrefs: () => ({ last: {}, setActive: () => {} }) }))
import { StartDeskPage } from "./StartDeskPage"

const html = () => renderToStaticMarkup(<MemoryRouter><StartDeskPage /></MemoryRouter>)

describe("StartDeskPage", () => {
  it("zeigt die Bereichs-Leiste und begrüßt mit Namen", () => {
    const h = html()
    expect(h).toContain('data-topbar="1"')
    expect(h).toMatch(/<h1[^>]*>[^<]*, till<\/h1>/)
  })
  it("hat eine App-Suche mit Beschriftung", () => {
    expect(html()).toMatch(/<input[^>]*aria-label="App suchen"/)
  })
  it("Buddy-Knopf mit Bild und Beschriftung steht vor den Bereichs-Kacheln", () => {
    const h = html()
    const buddy = h.indexOf('aria-label="Mit Buddy sprechen"')
    const firstArea = h.indexOf("Medienstudio")
    expect(buddy).toBeGreaterThan(-1)
    expect(buddy).toBeLessThan(firstArea)
    expect(h).toContain('src="/startdesk/buddy-knopf.webp"')
  })
  it("eine Kachel je gefülltem Bereich, mit Anzahl der Apps", () => {
    const h = html()
    for (const t of ["Medienstudio", "Schreibbüro", "Arbeiten mit Agenten"]) expect(h).toContain(t)
    expect(h).not.toContain("Freizeit")
    expect(h).toMatch(/data-area-tile="schreiben"[\s\S]*?>2<\/span>/)
  })
  it("Kacheln und Buddy-Knopf sind Knöpfe (type=button)", () => {
    const h = html()
    expect([...h.matchAll(/<button[^>]*data-area-tile="[a-z-]+"[^>]*>/g)].every((m) => m[0].includes('type="button"'))).toBe(true)
    expect(h).toMatch(/<button[^>]*type="button"[^>]*aria-label="Mit Buddy sprechen"|<button[^>]*aria-label="Mit Buddy sprechen"[^>]*type="button"/)
  })
})
