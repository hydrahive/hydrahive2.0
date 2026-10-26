import { describe, expect, it } from "vitest"
import { adminOfflineActions } from "../actionRegistry"
import { isAdminOverlayId, OVERLAY_BY_ACTION, OVERLAY_BY_PATH } from "./adminOverlayRegistry"

// Spec docs/specs/archiv-system.md, Admin-Konsole: eigenes Fenster „Archiv & Sicherung“
// (/admin?section=archive), Karte in „Wartung & Backups“ und Eintrag in „Admin-Bereiche“.
describe("Admin-Registry: Archiv & Sicherung", () => {
  it("archive ist ein gültiges Admin-Fenster", () => {
    expect(isAdminOverlayId("archive")).toBe(true)
  })

  it("Pfad /archive öffnet das Fenster", () => {
    expect(OVERLAY_BY_PATH["/archive"]).toBe("archive")
  })

  it("Eintrag „Archiv“ in den Admin-Bereichen öffnet das Fenster", () => {
    const entry = adminOfflineActions.find((a) => a.id === "archive")
    expect(entry?.path).toBe("/archive")
    expect(OVERLAY_BY_ACTION.archive).toBe("archive")
  })

  it("unbekannte Abschnitte bleiben ungültig", () => {
    expect(isAdminOverlayId("archiv")).toBe(false)
    expect(isAdminOverlayId(null)).toBe(false)
  })
})

// Plan docs/plans/admin-luecken-schliessen.md, Task 6: Föderation als Admin-Fenster.
describe("Admin-Registry: Föderation", () => {
  it("federation ist ein gültiges Admin-Fenster", () => {
    expect(isAdminOverlayId("federation")).toBe(true)
  })
  it("Pfad /federation öffnet das Fenster", () => {
    expect(OVERLAY_BY_PATH["/federation"]).toBe("federation")
  })
})
