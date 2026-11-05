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
      isAdministrator: false,
      isSystemAccount: false,
      buttonLabel: "Benutzermenü: mira, Nutzer, Instanz cockpit",
      systemAccountWarning: null,
    })
  })

  it("behandelt till mit Admin-Rechten als Administrator, nicht als Systemkonto", () => {
    const identity = getInstanceIdentity("till", "admin", { host: "192.168.178.2" })

    expect(identity.roleLabel).toBe("Administrator")
    expect(identity.roleBadge).toBe("ADMIN")
    expect(identity.isSystemAccount).toBe(false)
    expect(identity.buttonLabel).toBe("Benutzermenü: till, Administrator, Instanz 192.168.178.2")
    expect(identity.systemAccountWarning).toBeNull()
  })

  it.each(["admin", "Admin", "ADMIN"])("erkennt %s rollenunabhängig als Systemkonto", (username) => {
    const identity = getInstanceIdentity(username, "user", { host: "localhost:5173" })

    expect(identity.roleLabel).toBe("SYSTEM-ADMIN")
    expect(identity.isAdministrator).toBe(true)
    expect(identity.isSystemAccount).toBe(true)
    expect(identity.buttonLabel).toBe(`Benutzermenü: ${username}, SYSTEM-ADMIN, Instanz localhost:5173`)
    expect(identity.systemAccountWarning).toContain("getrennt")
  })

  it("verändert Benutzernamen nicht und klassifiziert Leerzeichen nicht als Systemkonto", () => {
    const identity = getInstanceIdentity(" admin ", "user", { host: "cockpit" })

    expect(identity.username).toBe(" admin ")
    expect(identity.isSystemAccount).toBe(false)
    expect(identity.systemAccountWarning).toBeNull()
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
