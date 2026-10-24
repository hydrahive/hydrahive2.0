// docs/specs/modul-update-alle.md: Zeilen des Ablaufs „Alle updaten“ → Fortschritt und Zusammenfassung.
import { describe, expect, it } from "vitest"
import { parseUpdateAll } from "./updateAllProgress"

const L = {
  start: (id: string) => `[modules] update ${id} …`,
  ok: (id: string, a: string, b: string) => `[modules] ${id}: fertig (${a} → ${b})`,
  fail: (id: string, why: string) => `[modules] ${id}: FEHLER – ${why}`,
}

describe("parseUpdateAll", () => {
  it("leer → Phase start, nichts gezählt", () => {
    expect(parseUpdateAll([], 3)).toEqual({ phase: "start", done: 0, total: 3, ok: [], failed: [], upToDate: false })
  })

  it("zählt fertige und fehlgeschlagene Module, merkt sich alt → neu und den Grund", () => {
    const p = parseUpdateAll([L.start("a"), L.ok("a", "1.0.0", "1.0.1"), L.start("b"), L.fail("b", "keine Schreibrechte"), L.start("c")], 3)
    expect(p.phase).toBe("modules")
    expect(p.done).toBe(2)
    expect(p.ok).toEqual([{ id: "a", from: "1.0.0", to: "1.0.1" }])
    expect(p.failed).toEqual([{ id: "b", reason: "keine Schreibrechte" }])
  })

  it("Bauen und Neustart werden als eigene Phasen erkannt", () => {
    const base = [L.start("a"), L.ok("a", "1", "2")]
    expect(parseUpdateAll([...base, "[modules] Frontend wird gebaut …"], 1).phase).toBe("build")
    expect(parseUpdateAll([...base, "[modules] Frontend gebaut", "[modules] Neustart angefordert"], 1).phase).toBe("restart")
  })

  it("Schlusszeile → Phase fertig", () => {
    const p = parseUpdateAll([L.start("a"), L.ok("a", "1", "2"), "[modules] Neustart angefordert", "[modules] Fertig: 1 aktualisiert, 0 fehlgeschlagen"], 1)
    expect(p.phase).toBe("finished")
  })

  it("„Alle Module sind aktuell“ → fertig ohne Arbeit", () => {
    expect(parseUpdateAll(["[modules] Alle Module sind aktuell"], 0)).toMatchObject({ phase: "finished", upToDate: true, done: 0 })
  })

  it("Gesamtzahl wächst, wenn der Server mehr Module meldet als erwartet", () => {
    const p = parseUpdateAll([L.ok("a", "1", "2"), L.ok("b", "1", "2"), L.ok("c", "1", "2")], 2)
    expect(p.done).toBe(3)
    expect(p.total).toBe(3)
  })

  it("Grund mit Bindestrich bleibt ganz", () => {
    expect(parseUpdateAll([L.fail("x", "a – b – c")], 1).failed).toEqual([{ id: "x", reason: "a – b – c" }])
  })

  it("fremde Zeilen (Build-Ausgabe, Abhängigkeiten) stören nicht", () => {
    const p = parseUpdateAll(["vite v8 building…", "[modules] Abhängigkeit videoeditor wird installiert …", L.ok("atelier", "1", "2")], 1)
    expect(p.done).toBe(1)
    expect(p.ok.map((o) => o.id)).toEqual(["atelier"])
  })
})
