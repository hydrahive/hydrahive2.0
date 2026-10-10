import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
import { HubCockpitCard, InstalledCockpitCard } from "./PluginCockpitCards"
import type { InstalledPlugin } from "@/features/plugins/types"

// React maskiert " als &quot;; „gesperrt“ = Attribut disabled="" (nicht die CSS-Klasse disabled:opacity-50).
const plain = (html: string) => html.replace(/&quot;/g, '"')
const DISABLED = /<button[^>]*\sdisabled=""/

const inst = (p: Partial<InstalledPlugin> = {}): InstalledPlugin => ({
  name: "file-search", version: "0.1.1", description: null, loaded: true, error: null, tools: [],
  installed_version: "0.1.1", available_version: "0.2.0", update_available: true, restart_needed: false, ...p,
})
const noop = () => {}

describe("Plugin-Karten im Cockpit", () => {
  it("Installiert: Plakette v0.1.1 → v0.2.0 und Knopf „Update verfügbar“", () => {
    const html = renderToStaticMarkup(<InstalledCockpitCard plugin={inst()} busy={false} onUpdate={noop} onUninstall={noop} />)
    expect(plain(html)).toContain('update_badge:{"from":"0.1.1","to":"0.2.0"}')
    expect(html).toMatch(/<button[^>]*>(<svg.*?<\/svg>)?update_available<\/button>/)   // Knopf, nicht nur title der Plakette
  })
  it("Installiert nach Aktualisieren ohne Neustart: „Neustart nötig“, kein „Update verfügbar“", () => {
    const html = renderToStaticMarkup(<InstalledCockpitCard plugin={inst({ restart_needed: true, update_available: false })} busy={false} onUpdate={noop} onUninstall={noop} />)
    expect(html).toContain("restart_needed")
    expect(html).not.toContain("update_available")
  })
  it("Installiert und aktuell: Knopf „Aktualisieren“, keine Plakette", () => {
    const html = renderToStaticMarkup(<InstalledCockpitCard plugin={inst({ update_available: false, available_version: "0.1.1" })} busy={false} onUpdate={noop} onUninstall={noop} />)
    expect(html).not.toContain("update_badge")
    expect(html).toContain(">update<")
  })
  it("Hub: installiert mit neuer Version → aktiver Knopf „Update verfügbar“ statt gesperrtem „Neu installieren“", () => {
    const hub = { name: "file-search", version: "0.2.0", description: "d" }
    const html = renderToStaticMarkup(<HubCockpitCard plugin={hub} action="update" busy={false} onInstall={noop} onUpdate={noop} />)
    expect(html).toContain("update_available")
    expect(html).not.toContain("reinstall")
    expect(html).not.toMatch(DISABLED)
  })
  it("Hub: installiert und aktuell → gesperrt", () => {
    const hub = { name: "git-stats", version: "0.1.1", description: "d" }
    const html = renderToStaticMarkup(<HubCockpitCard plugin={hub} action="installed" busy={false} onInstall={noop} onUpdate={noop} />)
    expect(html).toMatch(DISABLED)
  })
})
