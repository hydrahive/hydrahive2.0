// docs/specs/startdesktop.md (Punkt 4): Startseite nach dem Anmelden – Standard „start“, am Server gespeichert,
// alte Browser-Einstellung hh_landing wird einmal übernommen, wenn am Server noch nichts steht.
import { describe, expect, it } from "vitest"
import { LANDINGS, landingPath, resolveLanding } from "./landing"

describe("landing", () => {
  it("drei Wahlmöglichkeiten in fester Reihenfolge", () => {
    expect(LANDINGS).toEqual(["start", "buddy", "dashboard"])
  })
  it("Pfade", () => {
    expect(landingPath("start")).toBe("/start")
    expect(landingPath("buddy")).toBe("/buddy")
    expect(landingPath("dashboard")).toBe("/dashboard")
  })
  it("Server gewinnt, wenn er etwas anderes als den Standard hat", () => {
    expect(resolveLanding("dashboard", "buddy")).toEqual({ landing: "dashboard", migrate: false })
  })
  it("Server auf Standard und alte Browser-Wahl vorhanden → übernehmen und an den Server schreiben", () => {
    expect(resolveLanding("start", "dashboard")).toEqual({ landing: "dashboard", migrate: true })
    expect(resolveLanding("start", "buddy")).toEqual({ landing: "buddy", migrate: true })
  })
  it("nichts Altes oder Unsinn im Browser → Standard, nichts schreiben", () => {
    expect(resolveLanding("start", null)).toEqual({ landing: "start", migrate: false })
    expect(resolveLanding("start", "quatsch")).toEqual({ landing: "start", migrate: false })
    expect(resolveLanding("start", "start")).toEqual({ landing: "start", migrate: false })
  })
  it("unbekannter Server-Wert → Standard", () => {
    expect(resolveLanding("admin" as never, null)).toEqual({ landing: "start", migrate: false })
  })
})
