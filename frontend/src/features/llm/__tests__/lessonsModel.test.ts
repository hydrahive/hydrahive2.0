import { describe, expect, it } from "vitest"
import { LESSONS_OFF, lessonsChoice, lessonsValue } from "../lessonsModel"

describe("Modell für Lehren (docs/specs/lehren-mit-beleg.md 10a)", () => {
  it("leer = wie Chat, off = aus, sonst das Modell", () => {
    expect(lessonsChoice({ lessons_model: "" })).toBe("")
    expect(lessonsChoice({})).toBe("")
    expect(lessonsChoice({ lessons_model: "off" })).toBe(LESSONS_OFF)
    expect(lessonsChoice({ lessons_model: "ollama/gemma4:latest" })).toBe("ollama/gemma4:latest")
  })
  it("Auswahl wird so gespeichert, andere Felder bleiben", () => {
    const cfg = { default_model: "a/b", lessons_model: "x" }
    expect(lessonsValue(cfg, "")).toEqual({ default_model: "a/b", lessons_model: "" })
    expect(lessonsValue(cfg, LESSONS_OFF)).toEqual({ default_model: "a/b", lessons_model: "off" })
    expect(lessonsValue(cfg, "c/d").lessons_model).toBe("c/d")
  })
})
