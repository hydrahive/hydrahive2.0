// Plan docs/plans/admin-luecken-schliessen.md, Task 1: eine Zählung für Hub und Admin-Cockpit.
import { describe, expect, it } from "vitest"
import { countUnbound } from "./unbound"

const c = (host_bound?: boolean) => ({ host_bound })

describe("countUnbound", () => {
  it("leere Liste → 0", () => {
    expect(countUnbound([])).toBe(0)
  })
  it("zählt nur Zugänge, die ausdrücklich keinen Host haben", () => {
    expect(countUnbound([c(false), c(true), c(false)])).toBe(2)
  })
  it("alte Einträge ohne Feld gelten nicht als ungebunden", () => {
    expect(countUnbound([c(undefined), c(true)])).toBe(0)
  })
})
