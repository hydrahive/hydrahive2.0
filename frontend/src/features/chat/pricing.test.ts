import { describe, expect, it } from "vitest"
import { MICROS_PER_USD, formatCost, formatMicrosUsd } from "./pricing"

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
