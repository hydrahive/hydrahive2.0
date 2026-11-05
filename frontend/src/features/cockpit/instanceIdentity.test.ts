import { afterEach, describe, expect, it, vi } from "vitest"
import { compactInstanceHost, getInstanceHost, getInstanceIdentity } from "./instanceIdentity"

afterEach(() => vi.unstubAllGlobals())

describe("Instanzidentität", () => {
  it("beschriftet einen normalen Nutzer mit Rolle, Browserhost und vollständigem Menü-Label", () => {
    const identity = getInstanceIdentity("mira", "user", { host: "cockpit" })

    expect(identity).toEqual({
      username: "mira",
      roleLabel: "Nutzer",
      roleBadge: "NUTZER",
      host: "cockpit",
      shortHost: "cockpit",
      isAdmin: false,
      buttonLabel: "Benutzermenü: mira, Nutzer, Instanz cockpit",
      adminWarning: null,
    })
  })

  it("kennzeichnet admin als Systemadministrator und liefert den Warnhinweis", () => {
    const identity = getInstanceIdentity("admin", "admin", { host: "localhost:5173" })

    expect(identity.roleLabel).toBe("SYSTEM-ADMIN")
    expect(identity.isAdmin).toBe(true)
    expect(identity.buttonLabel).toBe("Benutzermenü: admin, SYSTEM-ADMIN, Instanz localhost:5173")
    expect(identity.adminWarning).toContain("getrennt")
  })

  it("kürzt lange Hosts mit stabiler, unterscheidbarer Kennung", () => {
    const first = compactInstanceHost("arbeitsplatz-eins.hydrahive.intern")
    const second = compactInstanceHost("arbeitsplatz-zwei.hydrahive.intern")

    expect(first.length).toBeLessThanOrEqual(12)
    expect(second.length).toBeLessThanOrEqual(12)
    expect(first).not.toBe(second)
  })

  it("liest den Host aus window.location und verwendet ohne Browserhost einen sicheren Fallback", () => {
    vi.stubGlobal("window", { location: { host: "hydrahive.intern:8443" } })
    expect(getInstanceHost()).toBe("hydrahive.intern:8443")

    vi.stubGlobal("window", undefined)
    expect(getInstanceHost()).toBe("unbekannte Instanz")
  })
})
