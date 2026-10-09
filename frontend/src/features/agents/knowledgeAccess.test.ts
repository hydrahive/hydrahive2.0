import { describe, expect, it } from "vitest"
import { buildAccess, defaultsFor, levelOf, sameAccess } from "./knowledgeAccess"

describe("levelOf", () => {
  it("max_level gewinnt, sonst Altfeld sensitive, sonst Standard je Typ", () => {
    expect(levelOf({ max_level: "privat", sensitive: true }, "project")).toBe("privat")
    expect(levelOf({ sensitive: true }, "project")).toBe("gesundheit")
    expect(levelOf({ sensitive: false }, "master")).toBe("normal")
    expect(levelOf(undefined, "master")).toBe("gesundheit")
    expect(levelOf({}, "specialist")).toBe("normal")
  })
})

describe("buildAccess", () => {
  it("speichert nur Abweichungen vom Standard", () => {
    expect(buildAccess("project", { scope: "project", projects: [], groups: [], max_level: "normal" })).toEqual({})
    expect(buildAccess("master", { scope: "user", projects: [], groups: [], max_level: "gesundheit" })).toEqual({})
  })
  it("übernimmt Projekte, Gruppen, Stufe, Bereich – ohne Dubletten und Leere", () => {
    expect(buildAccess("project", { scope: "user", projects: ["P1", "P1", ""], groups: ["G"], max_level: "privat" }))
      .toEqual({ scope: "user", projects: ["P1"], groups: ["G"], max_level: "privat" })
  })
  it("Buddy herabstufen wird gespeichert", () => {
    expect(buildAccess("master", { scope: "user", projects: [], groups: [], max_level: "normal" })).toEqual({ max_level: "normal" })
  })
  it("Standard passt zum Server (defaults_for)", () => {
    expect(defaultsFor("master")).toEqual({ scope: "user", max_level: "gesundheit" })
    expect(defaultsFor("project")).toEqual({ scope: "project", max_level: "normal" })
  })
})

describe("sameAccess", () => {
  it("Reihenfolge egal, Inhalt zählt", () => {
    expect(sameAccess({ groups: ["a", "b"] }, { groups: ["b", "a"] })).toBe(true)
    expect(sameAccess({ max_level: "privat" }, {})).toBe(false)
    expect(sameAccess(undefined, {})).toBe(true)
  })
})
