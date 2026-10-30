// Plan docs/plans/admin-reiter-system.md, Task 1: Reiter des System-Fensters.
import { describe, expect, it } from "vitest"
import type { HealthCheck } from "@/features/system/api"
import { parseSystemTab, systemTabList, systemTabs } from "./systemTabs"

const ok: HealthCheck = { name: "db", ok: true }
const kaputt: HealthCheck = { name: "disk", ok: false }
const t = (k: string) => k
const reiter = (checks: HealthCheck[], admin = true) => Object.fromEntries(systemTabs(checks, admin, t).map((r) => [r.id, r]))

describe("System-Reiter", () => {
  it("Admin: vier Reiter in fester Reihenfolge", () => {
    expect(systemTabList(true)).toEqual(["ueberblick", "netzwerk", "erweiterungen", "sicherung"])
  })
  it("Nicht-Admin: nur Überblick und Netzwerk (sonst wären die Reiter leer)", () => {
    expect(systemTabList(false)).toEqual(["ueberblick", "netzwerk"])
    expect(systemTabs([], false, t).map((r) => r.id)).toEqual(["ueberblick", "netzwerk"])
  })
  it("Rückfall auf Überblick, auch wenn ein Nicht-Admin einen Admin-Reiter in der Adresse hat", () => {
    expect(parseSystemTab(null, true)).toBe("ueberblick")
    expect(parseSystemTab("sicherung", true)).toBe("sicherung")
    expect(parseSystemTab("sicherung", false)).toBe("ueberblick")
    expect(parseSystemTab("netzwerk", false)).toBe("netzwerk")
  })
  it("Punkt am Überblick nur, wenn eine Gesundheitsprüfung nicht ok ist", () => {
    expect(reiter([ok, kaputt]).ueberblick.dot).toBe(true)
    expect(reiter([ok]).ueberblick.dot).toBe(false)
    expect(reiter([]).ueberblick.dot).toBe(false)
  })
  it("Beschriftung aus der Übersetzung", () => {
    expect(reiter([]).sicherung.label).toBe("tabs.sicherung")
  })
})
