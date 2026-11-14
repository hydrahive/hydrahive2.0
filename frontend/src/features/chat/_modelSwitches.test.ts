import { describe, expect, it } from "vitest"
import { readModelSwitches } from "./_modelSwitches"

describe("readModelSwitches", () => {
  it("liest gültige Wechsel", () => {
    const meta = { model_switches: [{ from_model: "a", to_model: "b", reason: "rate_limit" }] }
    expect(readModelSwitches(meta)).toEqual([{ from_model: "a", to_model: "b", reason: "rate_limit" }])
  })

  it("leer ohne Feld oder bei kaputten Einträgen", () => {
    expect(readModelSwitches(undefined)).toEqual([])
    expect(readModelSwitches({ model_switches: "x" })).toEqual([])
    expect(readModelSwitches({ model_switches: [null, { from_model: 1 }] })).toEqual([])
  })

  it("unbekannter Grund wird zu other", () => {
    const meta = { model_switches: [{ from_model: "a", to_model: "b", reason: "boom" }] }
    expect(readModelSwitches(meta)[0].reason).toBe("other")
  })
})
