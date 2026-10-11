import { describe, expect, it } from "vitest"
import { addonOutcome, lastRun } from "./addonsApi"

const run = (...body: string[]) => ["[hh2-addon] ===== 2026-10-11 10:00:00 Anfrage: install samba =====\n", ...body]

describe("addonOutcome – Ergebnis des letzten Laufs aus dem Log", () => {
  it("FERTIG für genau dieses Modul → ok", () => {
    expect(addonOutcome(run("x\n", "[hh2-addon] FERTIG: install samba ok\n"), "samba")).toBe("ok")
  })
  it("FERTIG für ein anderes Modul zählt nicht", () => {
    expect(addonOutcome(run("[hh2-addon] FERTIG: install vms ok\n"), "samba")).toBeNull()
  })
  it("FEHLER → failed", () => {
    expect(addonOutcome(run("[hh2-addon] FEHLER: install samba fehlgeschlagen\n"), "samba")).toBe("failed")
  })
  it("Lauf noch ohne Ende → null; ein ALTES FERTIG vor der Kopfzeile zählt nicht", () => {
    const lines = ["[hh2-addon] FERTIG: install samba ok\n", ...run("läuft\n")]
    expect(addonOutcome(lines, "samba")).toBeNull()
  })
  it("leeres Log → null", () => {
    expect(addonOutcome([], "samba")).toBeNull()
  })
})

describe("lastRun – nur der letzte Lauf", () => {
  it("schneidet ältere Läufe ab", () => {
    const lines = ["alt\n", ...run("neu\n")]
    expect(lastRun(lines)).toEqual(run("neu\n"))
  })
  it("ohne Kopfzeile: alles", () => {
    expect(lastRun(["a\n", "b\n"])).toEqual(["a\n", "b\n"])
  })
})
