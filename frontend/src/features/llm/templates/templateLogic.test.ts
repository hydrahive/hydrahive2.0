import { describe, expect, it } from "vitest"
import {
  compactChain, groupTemplates, isValidId, newTemplate, padChain, providerOf, sameProviderSteps, toBody, withOverrun,
} from "./templateLogic"

const t = (id: string, group: string, label = id) => ({ ...newTemplate(id), group, label }) as ReturnType<typeof newTemplate>

describe("Template-Logik", () => {
  it("gruppiert in fester Reihenfolge und sortiert nach Name", () => {
    const g = groupTemplates([t("z", "system"), t("b", "specialists", "Backend"), t("a", "specialists", "Alpha"),
      t("p", "personal")])
    expect(g.map((x) => x.group)).toEqual(["personal", "specialists", "system"])
    expect(g[1].items.map((x) => x.label)).toEqual(["Alpha", "Backend"])
  })

  it("erkennt gleichen Anbieter in der Kette", () => {
    expect(sameProviderSteps(["claude-opus-5-5", "openai-codex/gpt-5.6-terra", "MiniMax-M3.1-Flash"])).toBe(false)
    expect(sameProviderSteps(["claude-opus-5-5", "claude-sonnet-5"])).toBe(true)
    expect(sameProviderSteps(["openai-codex/a", "openai-codex/b"])).toBe(true)
    expect(sameProviderSteps(["claude-opus-5-5", ""])).toBe(false)
  })

  it("Anbieter aus der ID", () => {
    expect(providerOf("ollama/gemma4:latest")).toBe("ollama")
    expect(providerOf("claude-fable-5")).toBe("anthropic")
    expect(providerOf("MiniMax-M3.1-Flash")).toBe("minimax")
  })

  it("Kette auffüllen und verdichten", () => {
    expect(padChain(["a"])).toEqual(["a", "", ""])
    expect(padChain(["a", "b", "c", "d"])).toEqual(["a", "b", "c"])
    expect(compactChain(["a", " ", "c"])).toEqual(["a", "c"])
  })

  it("toBody schickt keine leeren Stufen und keine Metadaten", () => {
    const b = toBody({ ...newTemplate("x"), chain: ["a", "", "c"], revision: 4 })
    expect(b.chain).toEqual(["a", "c"])
    expect("revision" in b).toBe(false)
  })

  it("Template-ID", () => {
    expect(isValidId("uebersetzer")).toBe(true)
    expect(isValidId("Ü")).toBe(false)
    expect(isValidId("1abc")).toBe(false)
  })

  it("Überschreitung", () => {
    expect(withOverrun(60, 20)).toBe(72)
    expect(withOverrun(60, 0)).toBe(60)
  })
})
