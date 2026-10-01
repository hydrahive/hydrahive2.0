import { describe, expect, it } from "vitest"
import { isStale } from "./_staleBundle"

describe("isStale", () => {
  it("neuer Server-Stand als beim Laden → veraltet", () => {
    expect(isStale("bf6cd6e9", "e4d973c8")).toBe(true)
  })

  it("gleicher Stand → aktuell", () => {
    expect(isStale("e4d973c8", "e4d973c8")).toBe(false)
  })

  it("ohne bekannten Stand (z. B. Server ohne git) nie warnen", () => {
    expect(isStale(null, "e4d973c8")).toBe(false)
    expect(isStale("e4d973c8", null)).toBe(false)
    expect(isStale(null, null)).toBe(false)
  })
})
