// Task 0dda5420, Etappe Buddy: Maskottchen ist Tills bunte Hydra (public/hydra/), nicht mehr die alte blaue.
import { renderToStaticMarkup } from "react-dom/server"
import { existsSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { HydraMascot } from "./HydraMascot"
import { MASCOT_SRC, type MascotState } from "./mascotSrc"

const STATES: MascotState[] = ["idle", "working", "speaking", "sleeping", "confused", "celebrate", "thinking", "error"]

describe("HydraMascot", () => {
  it("jeder Zustand hat ein Bild der bunten Hydra, das wirklich vorhanden ist", () => {
    for (const s of STATES) {
      expect(MASCOT_SRC[s]).toBe(`/hydra/${s}.webp`)
      expect(existsSync(join(__dirname, "../../public", MASCOT_SRC[s])), s).toBe(true)
    }
  })
  it("kein Bezug mehr auf die alten Illustrationen", () => {
    expect(Object.values(MASCOT_SRC).some((p) => p.includes("/illustrations/"))).toBe(false)
  })
  it("Deko-Bild: leerer Alternativtext, Größe gesetzt, kein türkiser Leucht-Schatten der alten Hydra", () => {
    const html = renderToStaticMarkup(<HydraMascot state="thinking" size={30} />)
    expect(html).toContain('src="/hydra/thinking.webp"')
    expect(html).toContain('alt=""')
    expect(html).toContain('width="30"')
    expect(html).not.toContain("rgba(34,211,238")
  })
})
