// Plan docs/plans/farbstufen-kopffarben.md, Task 1: Helligkeitsstufen an EINER Stelle (index.css),
// Tailwind verweist nur darauf. Dazu die gemessenen Abstände und die Lesbarkeit der Schrift.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import tailwind from "../../../tailwind.config.js"

const CSS = readFileSync(join(__dirname, "..", "..", "index.css"), "utf8")
const STUFEN = ["grund", "tief", "box", "kopf", "innen", "hebung", "rand", "rand-hover"] as const

/** Stufe aus index.css lesen: `--hh-s-box: 23 32 48;` → [23, 32, 48]. */
function stufe(name: string): number[] {
  const m = CSS.match(new RegExp(`--hh-s-${name}:\\s*(\\d+)\\s+(\\d+)\\s+(\\d+)\\s*;`))
  if (!m) throw new Error(`Stufe --hh-s-${name} fehlt in index.css`)
  return m.slice(1, 4).map(Number)
}
function hex(h: string): number[] {
  return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16))
}
function leucht([r, g, b]: number[]): number {
  const f = (c: number) => { const x = c / 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4 }
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}
function kontrast(a: number[], b: number[]): number {
  const [x, y] = [leucht(a), leucht(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}

describe("Farbstufen", () => {
  it("jede Stufe steht genau einmal in index.css", () => {
    for (const s of STUFEN) {
      expect(CSS.match(new RegExp(`--hh-s-${s}:`, "g"))?.length, s).toBe(1)
    }
  })

  it("Tailwind kennt die Stufen als s-* und verweist nur auf die Variablen", () => {
    const farben = (tailwind as { theme: { extend: { colors: Record<string, unknown> } } }).theme.extend.colors.s as Record<string, string>
    for (const s of STUFEN) expect(farben[s], s).toBe(`rgb(var(--hh-s-${s}) / <alpha-value>)`)
  })

  it("jede Stufe ist heller als die darunter", () => {
    const folge = ["grund", "tief", "box", "kopf", "innen", "hebung"].map((s) => leucht(stufe(s)))
    for (let i = 1; i < folge.length; i++) expect(folge[i], `Stufe ${i}`).toBeGreaterThan(folge[i - 1])
  })

  it("gemessene Abstände: Box hebt sich ab, Kopf und Innenzeile sind sichtbar abgesetzt", () => {
    expect(kontrast(stufe("grund"), stufe("box"))).toBeGreaterThanOrEqual(1.2)
    expect(kontrast(stufe("box"), stufe("kopf"))).toBeGreaterThanOrEqual(1.1)
    expect(kontrast(stufe("box"), stufe("innen"))).toBeGreaterThanOrEqual(1.2)
    expect(kontrast(stufe("box"), stufe("rand"))).toBeGreaterThanOrEqual(1.5)
  })

  it("Haupt- und Nebentext sind auf jeder Fläche lesbar (WCAG 4,5:1)", () => {
    for (const s of ["grund", "tief", "box", "kopf", "innen", "hebung"]) {
      expect(kontrast(hex("#e8eef8"), stufe(s)), `Haupttext auf ${s}`).toBeGreaterThanOrEqual(4.5)
      expect(kontrast(hex("#9aa7bc"), stufe(s)), `Nebentext auf ${s}`).toBeGreaterThanOrEqual(4.5)
    }
  })

  it("die alten Cockpit-Variablen zeigen auf die Stufen", () => {
    expect(CSS).toMatch(/--cockpit-panel:\s*rgb\(var\(--hh-s-box\)\)/)
    expect(CSS).toMatch(/--cockpit-border:\s*rgb\(var\(--hh-s-rand\)\)/)
    expect(CSS).toMatch(/--cockpit-input:\s*rgb\(var\(--hh-s-tief\)\)/)
  })
})
