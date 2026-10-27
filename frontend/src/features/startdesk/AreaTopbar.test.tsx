// docs/specs/startdesktop.md: Bereichs-Leiste – ⌂ Start · Bereich ▾ · Apps des Bereichs · Kasten · Seitenknopf.
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import type { LucideIcon } from "lucide-react"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/i18n/HelpButton", () => ({ HelpButton: () => <span data-help="1" /> }))
vi.mock("@/features/vault/VaultBadge", () => ({ VaultBadge: () => null }))
vi.mock("@/features/cockpit/CockpitUserMenu", () => ({ CockpitUserMenu: () => <span data-user="1" /> }))
const { I } = vi.hoisted(() => ({ I: (() => null) as unknown as LucideIcon }))
vi.mock("./useAreas", async () => {
  const { fillAreas } = await import("./areaLogic")
  const items = ["/storyteller", "/notizbuch", "/scratchpad", "/studio", "/tonstudio", "/projects"]
    .map((p) => ({ path: p, icon: I, labelKey: p.slice(1), group: "working" }))
  return { useAreas: () => ({ areas: fillAreas(items, true), label: (i: { labelKey: string }) => `L:${i.labelKey}` }) }
})
const st = vi.hoisted(() => ({ active: null as string | null }))
vi.mock("./useAreaPrefs", () => ({ useAreaPrefs: () => ({ active: st.active, last: {}, setActive: () => {}, remember: () => {} }) }))
import { AreaTopbar } from "./AreaTopbar"

const render = (path: string, props: Parameters<typeof AreaTopbar>[0] = {}) =>
  renderToStaticMarkup(<MemoryRouter initialEntries={[path]}><AreaTopbar {...props} /></MemoryRouter>)
const tabs = (h: string) => {
  const nav = h.match(/<nav[^>]*aria-label="Apps im Bereich"[^>]*>([\s\S]*?)<\/nav>/)
  return nav ? [...nav[1].matchAll(/<button[^>]*>([^<]*)<\/button>/g)].map((m) => m[1]) : []
}

describe("AreaTopbar", () => {
  it("Start-Knopf führt zur Startseite", () => {
    expect(render("/storyteller")).toMatch(/<button[^>]*aria-label="Start"/)
  })
  it("oben links das neue Hydra-Logo statt Haus-Symbol und Text", () => {
    const h = render("/storyteller")
    const start = h.match(/<button[^>]*aria-label="Start"[^>]*>([\s\S]*?)<\/button>/)![1]
    expect(start).toContain('src="/brand/logo-schriftzug.webp"')
    expect(start).toContain('src="/brand/logo-emblem.webp"')
    expect(start).not.toContain("<svg")
  })
  it("Bereich folgt der App: Storyteller → Schreibbüro, nur dessen Apps als Reiter", () => {
    const h = render("/storyteller")
    expect(h).toMatch(/aria-haspopup="menu"[^>]*>[\s\S]*?Schreibbüro/)
    expect(tabs(h)).toEqual(["L:storyteller", "L:notizbuch", "L:scratchpad"])
  })
  it("Unterseite einer App markiert die App als aktiv", () => {
    const h = render("/studio/neu/1")
    expect(tabs(h)).toEqual(["L:studio", "L:tonstudio"])
    expect(h).toMatch(/<button[^>]*aria-current="page"[^>]*>L:studio<\/button>/)
  })
  it("Seite ohne Bereich: zuletzt aktiver Bereich vom Server", () => {
    st.active = "medien"
    expect(tabs(render("/profile"))).toEqual(["L:studio", "L:tonstudio"])
    st.active = null
    const h = render("/profile")
    expect(tabs(h)).toEqual([])
    expect(h).toContain("Bereich wählen")
  })
  it("Reiter sind auf dem Handy ausgeblendet", () => {
    expect(render("/storyteller")).toMatch(/<nav[^>]*class="[^"]*\bhidden\b[^"]*\bsm:flex\b[^"]*"[^>]*aria-label="Apps im Bereich"|<nav[^>]*aria-label="Apps im Bereich"[^>]*class="[^"]*\bhidden\b[^"]*\bsm:flex\b/)
  })
  it("Kasten-Knopf, Hilfe und Profil sind da", () => {
    const h = render("/storyteller")
    expect(h).toMatch(/<button[^>]*aria-label="Alle Apps"/)
    expect(h).toContain('data-help="1"')
    expect(h).toContain('data-user="1"')
  })
  it("Seitenknopf (action) und extraActions bleiben erreichbar", () => {
    const h = render("/buddy", { action: { label: "Buddy-Settings", path: "/buddy/settings" }, extraActions: <button type="button">Extra</button> })
    expect(h).toMatch(/<button[^>]*>Buddy-Settings<\/button>/)
    expect(h).toContain(">Extra</button>")
  })
})
