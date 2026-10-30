// Plan docs/plans/admin-reiter-archiv.md, Task 1: Reiter-Logik für alle Admin-Fenster.
import { describe, expect, it } from "vitest"
import { nextTab, parseTab, withTab } from "./adminTabs"

const LISTE = ["a", "b", "c"] as const

describe("parseTab", () => {
  it("gültiger Reiter bleibt", () => {
    expect(parseTab(LISTE, "b")).toBe("b")
    expect(parseTab(LISTE, "c")).toBe("c")
  })
  it("fehlend oder unbekannt: der erste Reiter", () => {
    expect(parseTab(LISTE, null)).toBe("a")
    expect(parseTab(LISTE, "")).toBe("a")
    expect(parseTab(LISTE, "quatsch")).toBe("a")
  })
  it("kein Prototyp-Name wird als Reiter akzeptiert", () => {
    expect(parseTab(LISTE, "toString")).toBe("a")
  })
})

describe("withTab", () => {
  it("hängt tab an und lässt andere Werte stehen", () => {
    expect(withTab("?section=archive", "b")).toBe("?section=archive&tab=b")
  })
  it("ersetzt ein vorhandenes tab", () => {
    expect(withTab("?section=archive&tab=a&x=1", "c")).toBe("?section=archive&tab=c&x=1")
  })
  it("ohne Suchteil", () => {
    expect(withTab("", "a")).toBe("?tab=a")
  })
})

describe("nextTab (Pfeiltasten)", () => {
  it("vorwärts und am Ende wieder vorn", () => {
    expect(nextTab(LISTE, "a", 1)).toBe("b")
    expect(nextTab(LISTE, "c", 1)).toBe("a")
  })
  it("rückwärts und am Anfang wieder hinten", () => {
    expect(nextTab(LISTE, "b", -1)).toBe("a")
    expect(nextTab(LISTE, "a", -1)).toBe("c")
  })
})
