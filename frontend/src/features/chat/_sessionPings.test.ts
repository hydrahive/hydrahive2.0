import { describe, expect, it } from "vitest"
import { emitSessionPing, onSessionPing } from "./_sessionPings"

describe("sessionPings", () => {
  it("leitet Pings nur an Hörer derselben Session weiter", () => {
    const a: string[] = []
    const b: string[] = []
    const offA = onSessionPing("s-a", (k) => a.push(k))
    const offB = onSessionPing("s-b", (k) => b.push(k))
    emitSessionPing("s-a", "start")
    emitSessionPing("s-b", "done")
    expect(a).toEqual(["start"])
    expect(b).toEqual(["done"])
    offA(); offB()
  })

  it("nach dem Abmelden kommt nichts mehr an", () => {
    const got: string[] = []
    const off = onSessionPing("s-c", (k) => got.push(k))
    off()
    emitSessionPing("s-c", "start")
    expect(got).toEqual([])
  })
})
