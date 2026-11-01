import { describe, expect, it } from "vitest"
import { MICROS_PER_USD, estimateCostUsd, formatCost, formatMicrosUsd } from "./pricing"

// Task a1b95d3b: Dashboard und Session-Analyse zeigten „€“ vor Dollar-Beträgen,
// ohne umzurechnen. Kosten sind Dollar-Preise, cost_micros = Tausendstel Cent.
describe("formatMicrosUsd", () => {
  it("rechnet cost_micros in Dollar um (1 $ = 100.000 micros)", () => {
    expect(MICROS_PER_USD).toBe(100_000)
    expect(formatMicrosUsd(22_306_000, "en")).toBe("$223.06")
    expect(formatMicrosUsd(22_306_000, "de")).toBe("$223,06")
    expect(formatMicrosUsd(100_000, "en")).toBe("$1.00")
  })

  it("zeigt kleine Beträge wie im Chat", () => {
    expect(formatMicrosUsd(5_000, "en")).toBe("$0.05")
    expect(formatMicrosUsd(300, "en")).toBe("< $0.01")
    expect(formatMicrosUsd(0, "en")).toBe("$0.00")
  })

  it("nie ein Euro-Zeichen", () => {
    for (const m of [0, 1, 999, 50_000, 12_345_678]) {
      expect(formatMicrosUsd(m, "de")).not.toContain("€")
    }
  })

  it("nutzt denselben Formatierer wie die Chat-Kosten", () => {
    expect(formatMicrosUsd(1_234_500, "de")).toBe(formatCost(12.345, "de"))
  })
})

// MiniMax M3.x (Spec docs/specs/minimax-m3.md): Preise aus platform.minimax.io, Stand 01.11.2026.
describe("MiniMax-Preise", () => {
  const M = (n: number) => n * 1_000_000
  it("M3.1-Flash: 0,15 ein, 0,60 aus, 0,015 Cache lesen", () => {
    expect(estimateCostUsd("MiniMax-M3.1-Flash", { input: M(1), output: M(1), cache_read: M(1) })).toBeCloseTo(0.765, 6)
  })
  it("M3: 0,30 ein, 1,20 aus, 0,06 Cache lesen (mit Anbieter-Vorsatz)", () => {
    expect(estimateCostUsd("MiniMax-M3", { input: M(2), output: M(1) })).toBeCloseTo(1.8, 6)
    expect(estimateCostUsd("minimax/MiniMax-M3", { cache_read: M(1) })).toBeCloseTo(0.06, 6)
  })
  it("Flash wird nicht mit M3 verwechselt", () => {
    expect(estimateCostUsd("MiniMax-M3.1-Flash", { input: M(1) })).toBeCloseTo(0.15, 6)
    expect(estimateCostUsd("MiniMax-M3", { input: M(1) })).toBeCloseTo(0.30, 6)
  })
  it("M2.x bleibt eine Schätzung, abab hat keinen Preis mehr", () => {
    expect(estimateCostUsd("MiniMax-M2.7", { input: M(1) })).toBeCloseTo(0.30, 6)
    expect(estimateCostUsd("abab6.5s-chat", { input: M(1) })).toBeNull()
  })
})
