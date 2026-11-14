import { describe, expect, it } from "vitest"
import { parseLlmTab, templateFromParams } from "./llmTabs"

describe("Reiter des Fensters KI-Modelle aus der Adresse", () => {
  it("bekannte Reiter, sonst Anbieter", () => {
    expect(parseLlmTab("templates")).toBe("templates")
    expect(parseLlmTab("providers")).toBe("providers")
    expect(parseLlmTab("quatsch")).toBe("providers")
    expect(parseLlmTab(null)).toBe("providers")
  })
  it("Template nur mit gültiger Kennung", () => {
    expect(templateFromParams(new URLSearchParams("template=projekt-master"))).toBe("projekt-master")
    for (const bad of ["template=../x", "template=A B", "template=", ""])
      expect(templateFromParams(new URLSearchParams(bad)), bad).toBeNull()
  })
})
