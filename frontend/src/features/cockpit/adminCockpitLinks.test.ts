// Plan docs/plans/admin-cockpit-kompakt.md: jeder Einstieg genau einmal, nichts geht verloren.
import { describe, expect, it } from "vitest"
import { ADMIN_AREAS, OPS_LINKS } from "./adminCockpitLinks"
import { OVERLAY_BY_ACTION, OVERLAY_BY_PATH } from "./admin/adminOverlayRegistry"

const alle = [...ADMIN_AREAS, ...OPS_LINKS]

describe("Admin-Cockpit-Einstiege", () => {
  it("jeder Pfad steht genau einmal auf der Seite", () => {
    const pfade = alle.map((l) => l.path)
    expect(new Set(pfade).size).toBe(pfade.length)
  })

  it("Verwaltung: System, Benutzer, Freigaben, Module, Extensions, Plugins, Credentials, Archiv", () => {
    expect(ADMIN_AREAS.map((l) => l.path)).toEqual(
      ["/system", "/users", "/access", "/modules", "/extensions", "/plugins", "/credentials", "/archive"])
  })

  it("was bisher nur in den entfernten Kästen stand, bleibt erreichbar: Freigaben, Gitea (Extensions), Globale Einstellungen", () => {
    const pfade = alle.map((l) => l.path)
    expect(pfade).toContain("/access")
    expect(pfade).toContain("/extensions")
    expect(pfade).toContain("/system/settings")
  })

  it("alle bisherigen Betriebs-Einstiege bleiben", () => {
    for (const p of ["/llm", "/mcp", "/skills", "/vms", "/containers", "/nodes", "/jobs", "/scheduled-tasks", "/federation", "/zahnfee-config"]) {
      expect(OPS_LINKS.map((l) => l.path), p).toContain(p)
    }
  })

  it("jeder Einstieg öffnet ein Admin-Fenster oder ist eine bekannte eigene Seite", () => {
    const eigeneSeiten = new Set(["/skills"])
    for (const l of alle) {
      const fenster = OVERLAY_BY_PATH[l.path] ?? (l.id ? OVERLAY_BY_ACTION[l.id] : undefined)
      expect(fenster ?? (eigeneSeiten.has(l.path) ? "seite" : undefined), l.path).toBeDefined()
    }
  })

  it("jeder Einstieg hat einen kurzen Namen", () => {
    for (const l of alle) expect(l.title.length, l.path).toBeGreaterThan(1)
  })
})
