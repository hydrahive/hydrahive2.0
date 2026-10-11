import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
import { AddonsView, type AddonsViewProps } from "./AddonsView"
import type { AddonItem } from "./addonsApi"

const item = (p: Partial<AddonItem> & Pick<AddonItem, "id">): AddonItem => ({
  installed: false, enabled: false, restarts_service: false, requires: [], hint: null, ...p,
})
const ITEMS: AddonItem[] = [
  item({ id: "containers", restarts_service: true }), item({ id: "vms", restarts_service: true }),
  item({ id: "samba", installed: true, enabled: true }), item({ id: "whatsapp" }),
  item({ id: "voice", requires: ["containers"] }), item({ id: "tailscale" }),
]
const noop = () => {}
const props = (p: Partial<AddonsViewProps> = {}): AddonsViewProps => ({
  items: ITEMS, running: null, target: null, phase: "idle", log: [], error: null,
  onAsk: noop, onConfirm: noop, onClose: noop, ...p,
})
const plain = (html: string) => html.replace(/&quot;/g, '"')
// Knöpfe „Installieren“ mit data-addon – gesperrt = Attribut disabled="".
const button = (html: string, id: string) => html.match(new RegExp(`<button[^>]*data-addon="${id}"[^>]*>`))?.[0] ?? ""

describe("Karte Zusatz-Module", () => {
  it("eine Zeile je Modul in fester Reihenfolge", () => {
    const html = renderToStaticMarkup(<AddonsView {...props()} />)
    const order = [...html.matchAll(/data-addon-row="([a-z]+)"/g)].map((m) => m[1])
    expect(order).toEqual(["containers", "vms", "samba", "whatsapp", "voice", "tailscale"])
  })
  it("installiert: Plakette statt Knopf; nicht installiert: Knopf „Installieren“", () => {
    const html = renderToStaticMarkup(<AddonsView {...props()} />)
    expect(button(html, "samba")).toBe("")
    expect(html).toMatch(/data-addon-row="samba"[\s\S]*?addons\.installed/)
    expect(button(html, "whatsapp")).not.toBe("")
    expect(button(html, "whatsapp")).not.toMatch(/disabled=""/)
  })
  it("während eines Laufs sind alle Knöpfe gesperrt und das laufende Modul ist markiert", () => {
    const html = renderToStaticMarkup(<AddonsView {...props({ running: "vms", target: "vms", phase: "running" })} />)
    for (const id of ["containers", "whatsapp", "voice", "tailscale"]) expect(button(html, id)).toMatch(/disabled=""/)
    expect(html).toMatch(/data-addon-row="vms"[\s\S]*?addons\.running_badge/)
  })
  it("Rückfrage bei VMs nennt den kurzen Neustart, bei WhatsApp nicht", () => {
    const vms = renderToStaticMarkup(<AddonsView {...props({ target: "vms", phase: "confirm" })} />)
    expect(vms).toContain("addons.confirm_restart")
    const wa = renderToStaticMarkup(<AddonsView {...props({ target: "whatsapp", phase: "confirm" })} />)
    expect(wa).not.toContain("addons.confirm_restart")
    expect(plain(wa)).toContain('addons.confirm:{"name":"addons.name.whatsapp"}')
  })
  it("Rückfrage bei Voice nennt die Abhängigkeit, wenn Container fehlen", () => {
    const html = renderToStaticMarkup(<AddonsView {...props({ target: "voice", phase: "confirm" })} />)
    expect(plain(html)).toContain('addons.confirm_requires:{"names":"addons.name.containers"}')
    const withC = ITEMS.map((i) => (i.id === "containers" ? { ...i, installed: true } : i))
    expect(renderToStaticMarkup(<AddonsView {...props({ items: withC, target: "voice", phase: "confirm" })} />))
      .not.toContain("addons.confirm_requires")
  })
  it("WSL-Hinweis nur bei den betroffenen Modulen", () => {
    const wsl = ITEMS.map((i) => (i.id === "vms" ? { ...i, hint: "wsl" as const } : i))
    const html = renderToStaticMarkup(<AddonsView {...props({ items: wsl })} />)
    expect(html.match(/addons\.hint_wsl/g)?.length).toBe(1)
    expect(html).toMatch(/data-addon-row="vms"[\s\S]*?addons\.hint_wsl[\s\S]*?data-addon-row="samba"/)
  })
  it("Log wird beim Lauf angezeigt, Fehlertext bei failed", () => {
    const running = renderToStaticMarkup(<AddonsView {...props({ target: "samba", phase: "running", running: "samba", log: ["[hh2-addon] Installiere samba\n"] })} />)
    expect(running).toContain("[hh2-addon] Installiere samba")
    const failed = renderToStaticMarkup(<AddonsView {...props({ target: "samba", phase: "failed", error: "addon_busy" })} />)
    expect(failed).toContain("addon_busy")
  })
  it("Liste noch nicht geladen: kein Absturz, kein Knopf", () => {
    const html = renderToStaticMarkup(<AddonsView {...props({ items: null })} />)
    expect(html).not.toContain("data-addon=")
  })
})
