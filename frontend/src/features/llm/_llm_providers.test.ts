import { describe, expect, it } from "vitest"
import { KNOWN_PROVIDERS, providerName } from "./_llm_providers"

describe("LLM-Anbieter: DeepSeek (Spec deepseek-provider)", () => {
  it("steht in der Liste mit Namen und Schlüssel-Hinweis", () => {
    const ds = KNOWN_PROVIDERS.find((p) => p.id === "deepseek")
    expect(ds?.name).toBe("DeepSeek")
    expect(ds?.placeholder).toBe("sk-...")
    expect(providerName("deepseek")).toBe("DeepSeek")
  })

  it("braucht keinen eigenen Endpunkt und kein OAuth", () => {
    const ds = KNOWN_PROVIDERS.find((p) => p.id === "deepseek") as Record<string, unknown> | undefined
    expect(ds?.needsApiBase).toBeUndefined()
    expect(ds?.auth).toBeUndefined()
  })
})
