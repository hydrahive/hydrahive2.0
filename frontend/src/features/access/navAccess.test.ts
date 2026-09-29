import { describe, expect, it } from "vitest"
import { capabilityForPath, pathAllowed } from "./navAccess"
import type { MyAccess } from "./types"

const user: MyAccess = {
  admin: false,
  capabilities: { "module.homeassistant": "use" },
  declared: ["core.vms", "core.containers", "core.federation", "module.homeassistant", "module.voice"],
  groups: [],
}

describe("navAccess", () => {
  it("ordnet Pfade Funktionen zu", () => {
    expect(capabilityForPath("/vms")).toBe("core.vms")
    expect(capabilityForPath("/containers/abc")).toBe("core.containers")
    expect(capabilityForPath("/federation")).toBe("core.federation")
    expect(capabilityForPath("/chat")).toBeNull()
  })

  it("Modul-Pfade über die Modul-ID", () => {
    expect(capabilityForPath("/voice", { "/voice": "voice" })).toBe("module.voice")
    expect(capabilityForPath("/voice/settings", { "/voice": "voice" })).toBe("module.voice")
  })

  it("sperrt deklarierte Funktion ohne Freigabe", () => {
    expect(pathAllowed("/vms", user)).toBe(false)
    expect(pathAllowed("/voice", user, { "/voice": "voice" })).toBe(false)
  })

  it("lässt freigegebene, offene und nicht deklarierte Pfade durch", () => {
    expect(pathAllowed("/homeassistant", user, { "/homeassistant": "homeassistant" })).toBe(true)
    expect(pathAllowed("/chat", user)).toBe(true)
    expect(pathAllowed("/blueprint", user, { "/blueprint": "blueprint" })).toBe(true)
  })

  it("Admin und unbekannter Stand sperren nichts", () => {
    expect(pathAllowed("/vms", { ...user, admin: true })).toBe(true)
    expect(pathAllowed("/vms", null)).toBe(true)
  })
})
