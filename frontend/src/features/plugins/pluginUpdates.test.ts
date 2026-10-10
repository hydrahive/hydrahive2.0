import { describe, expect, it } from "vitest"
import { hubCardAction, installedTabLabel, outdatedNames, updateBadge } from "./pluginUpdates"
import type { InstalledPlugin } from "./types"

// docs/specs/plugin-updates.md – Anlass: file-search 0.2.0 im Hub, installiert 0.1.1, nichts angezeigt.
const inst = (name: string, p: Partial<InstalledPlugin> = {}): InstalledPlugin => ({
  name, version: "0.1.1", description: null, loaded: true, error: null, tools: [],
  installed_version: "0.1.1", available_version: null, update_available: false, restart_needed: false, ...p,
})

describe("Plugin-Updates", () => {
  it("Plakette: Update verfügbar mit Versionen", () => {
    expect(updateBadge(inst("fs", { update_available: true, available_version: "0.2.0" })))
      .toEqual({ kind: "update", from: "0.1.1", to: "0.2.0" })
  })
  it("Plakette: Neustart nötig hat Vorrang (nach Aktualisieren ohne Neustart)", () => {
    expect(updateBadge(inst("fs", { restart_needed: true, update_available: true, available_version: "0.3.0" })))
      .toEqual({ kind: "restart" })
  })
  it("keine Plakette, wenn aktuell – auch bei älterem Backend ohne die Felder", () => {
    expect(updateBadge(inst("fs"))).toBeNull()
    const old = { name: "fs", version: "0.1.1", description: null, loaded: true, error: null, tools: [] } as InstalledPlugin
    expect(updateBadge(old)).toBeNull()
  })
  it("Liste der veralteten Plugins (für „Alle updaten“), ohne die, die nur noch Neustart brauchen", () => {
    const list = [inst("a", { update_available: true, available_version: "1" }), inst("b"),
                  inst("c", { update_available: true, available_version: "2", restart_needed: true })]
    expect(outdatedNames(list)).toEqual(["a"])
  })
  it("Hub-Karte: nicht installiert → Installieren; installiert + Update → Update; sonst gesperrt", () => {
    const byName = new Map([["fs", inst("fs", { update_available: true, available_version: "0.2.0" })], ["gs", inst("gs")]])
    expect(hubCardAction("neu", byName)).toBe("install")
    expect(hubCardAction("fs", byName)).toBe("update")
    expect(hubCardAction("gs", byName)).toBe("installed")
  })
  it("Reiter-Beschriftung mit Anzahl Updates", () => {
    const t = (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k)
    expect(installedTabLabel(t, 4, 0)).toBe("tab_installed (4)")
    expect(installedTabLabel(t, 4, 1)).toBe('tab_installed (4 · update_count:{"count":1})')
  })
})
