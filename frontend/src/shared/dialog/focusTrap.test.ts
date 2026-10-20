import { describe, expect, it } from "vitest"
import { oberster, tabZiel } from "./focusTrap"

// docs/specs/ui-standard.md, Regel 6: Tab bleibt im offenen Dialog.
// Ohne jsdom: Elemente als einfache Objekte, der Container kennt seine Kinder.
type El = HTMLElement
const el = (name: string) => ({ name }) as unknown as El
const container = (kinder: El[]) => {
  const c = { name: "dialog", contains: (x: unknown) => x === c || kinder.includes(x as El) } as unknown as El
  return c
}

describe("tabZiel – Fokusfalle im Dialog", () => {
  const a = el("a"), b = el("b"), c = el("c")
  const dlg = container([a, b, c])
  const liste = [a, b, c]

  it("Tab auf dem letzten Element springt zum ersten", () => {
    expect(tabZiel(liste, c, false, dlg)).toBe(a)
  })
  it("Shift+Tab auf dem ersten Element springt zum letzten", () => {
    expect(tabZiel(liste, a, true, dlg)).toBe(c)
  })
  it("Tab in der Mitte: Browser macht weiter (null)", () => {
    expect(tabZiel(liste, a, false, dlg)).toBeNull()
    expect(tabZiel(liste, b, true, dlg)).toBeNull()
  })
  it("Fokus außerhalb des Dialogs wird hineingeholt", () => {
    const draussen = el("hinten")
    expect(tabZiel(liste, draussen, false, dlg)).toBe(a)
    expect(tabZiel(liste, draussen, true, dlg)).toBe(c)
    expect(tabZiel(liste, null, false, dlg)).toBe(a)
  })
  it("Fokus auf dem Dialog selbst + Shift+Tab geht zum letzten", () => {
    expect(tabZiel(liste, dlg, true, dlg)).toBe(c)
  })
  it("Dialog ohne Bedienelemente behält den Fokus auf sich", () => {
    expect(tabZiel([], el("x"), false, dlg)).toBe(dlg)
  })
})

describe("oberster – welcher Dialog bekommt die Tastatur", () => {
  // closest() simuliert: geschlossen = aria-hidden/inert/hidden an sich oder einem Vorfahren
  const dlg = (name: string, geschlossen = false) =>
    ({ name, closest: () => (geschlossen ? {} : null) }) as unknown as HTMLElement

  it("geschlossener Dialog dahinter im DOM (HelpDrawer) zählt nicht", () => {
    const admin = dlg("admin"), hilfeZu = dlg("hilfe", true)
    expect(oberster([admin, hilfeZu])).toBe(admin)
  })
  it("verschachtelt: der zuletzt geöffnete offene gewinnt", () => {
    const a = dlg("a"), b = dlg("b")
    expect(oberster([a, b])).toBe(b)
  })
  it("nur geschlossene → keiner", () => {
    expect(oberster([dlg("x", true)])).toBeNull()
  })
})
