import { describe, expect, it } from "vitest"
import { scoreTone } from "./harnessDoctorScore"

describe("HarnessDoctorPanel", () => {
  it("ordnet Scorebereiche stabil zu", () => {
    expect(scoreTone(100)).toContain("emerald")
    expect(scoreTone(80)).toContain("emerald")
    expect(scoreTone(79)).toContain("amber")
    expect(scoreTone(60)).toContain("amber")
    expect(scoreTone(59)).toContain("rose")
  })
})
