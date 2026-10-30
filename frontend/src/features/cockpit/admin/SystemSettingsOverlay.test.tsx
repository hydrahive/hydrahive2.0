// Plan docs/plans/admin-reiter-einstellungen.md, Task 2: ein Reiter je Gruppe, Adresse `gruppe=`.
import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

const h = vi.hoisted(() => ({
  settings: [
    { key: "web.a", group: "Websuche", label: "A", type: "text", value: "", help: "", overridden: false, is_set: false },
    { key: "mail.b", group: "Mail", label: "B", type: "text", value: "", help: "", overridden: false, is_set: false },
    { key: "mail.c", group: "Mail", label: "C", type: "text", value: "", help: "", overridden: false, is_set: false },
    { key: "ha.d", group: "Home Assistant", label: "D", type: "text", value: "", help: "", overridden: false, is_set: false },
  ],
}))
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/features/system/settingsApi", () => ({ settingsApi: { list: vi.fn(() => new Promise(() => {})), update: vi.fn() } }))
import type { EditableSetting } from "@/features/system/settingsApi"
import { SettingsView } from "./SystemSettingsOverlay"

const render = (url: string) =>
  renderToStaticMarkup(<MemoryRouter initialEntries={[url]}>
    <SettingsView settings={h.settings as EditableSetting[]} failed={failed} onSaved={() => {}} onFailed={() => {}} />
  </MemoryRouter>)
let failed: ReadonlySet<string> = new Set()
const labels = (out: string) => [...out.matchAll(/text-sm font-medium text-\[#e8eef8\]">([^<]+)</g)].map((m) => m[1])

describe("Globale Einstellungen", () => {
  it("ein Reiter je Gruppe, mit Anzahl", () => {
    const out = render("/admin?section=system-settings")
    expect(out.match(/role="tab"/g)).toHaveLength(3)
    expect(out).toMatch(/id="settings-tab-home-assistant"/)
  })
  it("ohne Angabe: erste Gruppe", () => {
    expect(labels(render("/admin?section=system-settings"))).toEqual(["A"])
  })
  it("gruppe= aus der Adresse", () => {
    expect(labels(render("/admin?section=system-settings&gruppe=mail"))).toEqual(["B", "C"])
  })
  it("Punkt am Reiter der Gruppe, deren Speichern fehlschlug", () => {
    failed = new Set(["mail.c"])
    const out = render("/admin?section=system-settings")
    failed = new Set()
    expect(out).toContain('data-tab-dot="mail"')
    expect(out).not.toContain('data-tab-dot="websuche"')
  })
  it("liest nicht tab= (das gehört dem System-Fenster dahinter)", () => {
    expect(labels(render("/admin?section=system&tab=mail"))).toEqual(["A"])
  })
})
