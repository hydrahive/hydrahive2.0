// Plan docs/plans/farbstufen-kopffarben.md, Task 1: Helligkeitsstufen an EINER Stelle (index.css),
// Tailwind verweist nur darauf. Dazu die gemessenen Abstände und die Lesbarkeit der Schrift.
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

const CSS = readFileSync(join(__dirname, "..", "..", "index.css"), "utf8")
const TAILWIND = readFileSync(join(__dirname, "..", "..", "..", "tailwind.config.js"), "utf8")
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

/** Alle Kern-Quelldateien (ohne src/modules: die gehören den Modul-Repos, ohne Tests). */
function kernDateien(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n)
    if (statSync(p).isDirectory()) return n === "modules" ? [] : kernDateien(p)
    return /\.(tsx?|css)$/.test(n) && !/\.test\.tsx?$/.test(n) ? [p] : []
  })
}

/** Neutrales Dunkelblau/-grau der alten Cockpit-Flächen: dunkel und kaum gesättigt.
 *  Akzentflächen (Cyan-Knopf #163248, Etikett #1c2940 …) sind gesättigter und bleiben erlaubt. */
const AUSWAHL_TOENE = new Set(["1c2940", "30243a"]) // „ausgewählt“-Markierungen, keine Flächenstufe

function istNeutralDunkel(h: string): boolean {
  if (AUSWAHL_TOENE.has(h.toLowerCase())) return false
  const [r, g, b] = hex(`#${h}`)
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  const hell = (max + min) / 2 / 255
  const satt = max === min ? 0 : (max - min) / (255 - Math.abs(max + min - 255))
  return hell < 0.25 && satt < 0.42
}

describe("Farbstufen", () => {
  it("jede Stufe steht genau einmal in index.css", () => {
    for (const s of STUFEN) {
      expect(CSS.match(new RegExp(`--hh-s-${s}:`, "g"))?.length, s).toBe(1)
    }
  })

  it("Tailwind kennt die Stufen als s-* und verweist nur auf die Variablen", () => {
    for (const s of STUFEN) expect(TAILWIND, s).toContain(`"${s}": "rgb(var(--hh-s-${s}) / <alpha-value>)"`)
    // Kein Hex-Wert in der s-Gruppe: die Werte stehen nur in index.css.
    const gruppe = TAILWIND.match(/\n\s+s: \{([^}]*)\}/)?.[1]
    expect(gruppe).toContain("--hh-s-box")
    expect(gruppe).not.toMatch(/#[0-9a-f]{6}/i)
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

  it("Wächter: keine festen neutralen Dunkeltöne mehr für Flächen und Ränder (Module ausgenommen)", () => {
    const funde: string[] = []
    for (const datei of kernDateien(join(__dirname, "..", ".."))) {
      const text = readFileSync(datei, "utf8")
      for (const m of text.matchAll(/(?:bg|border(?:-[trblxy])?|from|to|via|ring|divide)-\[#([0-9a-fA-F]{6})\]/g)) {
        if (istNeutralDunkel(m[1])) funde.push(`${datei.split("/src/")[1]}: ${m[0]}`)
      }
      for (const m of text.matchAll(/text-\[#(8d9ab0|7d8aa0|718097)\]/gi)) funde.push(`${datei.split("/src/")[1]}: ${m[0]}`)
    }
    expect(funde).toEqual([])
  })

  it("schwebende Fenster und Menüs liegen auf der Box-Stufe, nicht eingelassen (tief)", () => {
    const funde: string[] = []
    for (const datei of kernDateien(join(__dirname, "..", ".."))) {
      for (const m of readFileSync(datei, "utf8").matchAll(/["`]([^"`\n]*\bbg-s-tief\b[^"`\n]*)["`]/g)) {
        if (/\b(fixed|absolute)\b/.test(m[1]) && /\bshadow-(xl|2xl)\b/.test(m[1])) funde.push(`${datei.split("/src/")[1]}: ${m[1].slice(0, 80)}`)
      }
    }
    expect(funde).toEqual([])
  })

  it("die alten Cockpit-Variablen zeigen auf die Stufen", () => {
    expect(CSS).toMatch(/--cockpit-panel:\s*rgb\(var\(--hh-s-box\)\)/)
    expect(CSS).toMatch(/--cockpit-border:\s*rgb\(var\(--hh-s-rand\)\)/)
    expect(CSS).toMatch(/--cockpit-input:\s*rgb\(var\(--hh-s-tief\)\)/)
  })
})
