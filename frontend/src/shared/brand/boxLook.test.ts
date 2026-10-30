// Plan docs/plans/farbstufen-kopffarben.md, Task 2: Kopffarbe + Zustand einer Box.
// Regel: Jede Box mit Thema trägt die Farbe ihres Hydra-Kopfs. Warnung/Fehler übermalen sie (gelb/rot).
import { describe, expect, it } from "vitest"
import { boxLook, STATUS_FARBE } from "./boxLook"
import { BOX_THEMES } from "./boxThemes"

describe("boxLook", () => {
  it("ohne Thema und ohne Zustand: neutral, kein Streifen, kein Schild", () => {
    expect(boxLook()).toEqual({ streifen: null, kopfTon: null, rand: null, schild: null })
  })

  it("jedes Thema hat eine eigene Kopffarbe", () => {
    const farben = Object.values(BOX_THEMES).map((t) => t.farbe)
    expect(new Set(farben).size).toBe(5)
    for (const f of farben) expect(f).toMatch(/^#[0-9a-f]{6}$/)
  })

  it("Thema ohne Zustand: Streifen in Kopffarbe, schwache Tönung, normaler Rand, kein Schild", () => {
    const l = boxLook("werkzeug")
    expect(l.streifen).toBe(BOX_THEMES.werkzeug.farbe)
    expect(l.kopfTon).toBe("rgb(249 115 22 / 0.09)")
    expect(l.rand).toBeNull()
    expect(l.schild).toBeNull()
  })

  it("Warnung übermalt die Kopffarbe: gelber Streifen, stärkere Tönung, gelber Rand, Schild", () => {
    const l = boxLook("ideen", "warnung")
    expect(l.streifen).toBe(STATUS_FARBE.warnung)
    expect(l.kopfTon).toBe("rgb(251 191 36 / 0.16)")
    expect(l.rand).toBe("rgb(251 191 36 / 0.45)")
    expect(l.schild).toBe("warnung")
  })

  it("Fehler ist rot – auch bei einer Box, deren Kopf selbst gelb ist (Professor)", () => {
    const l = boxLook("wissen", "fehler")
    expect(l.streifen).toBe(STATUS_FARBE.fehler)
    expect(l.streifen).not.toBe(BOX_THEMES.wissen.farbe)
    expect(l.schild).toBe("fehler")
  })

  it("ok: Kopffarbe bleibt, nur das Schild „Läuft“ kommt dazu", () => {
    const l = boxLook("status", "ok")
    expect(l.streifen).toBe(BOX_THEMES.status.farbe)
    expect(l.rand).toBeNull()
    expect(l.schild).toBe("ok")
  })

  it("Zustand ohne Thema: Warnung/Fehler trotzdem farbig, ok ohne Streifen", () => {
    expect(boxLook(undefined, "fehler").streifen).toBe(STATUS_FARBE.fehler)
    expect(boxLook(undefined, "ok")).toEqual({ streifen: null, kopfTon: null, rand: null, schild: "ok" })
  })
})
