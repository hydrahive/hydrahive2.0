import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import type { RegistryModel } from "@/features/llm/api"
import { FallbackModelsSelector } from "./_FallbackModelsSelector"

function m(id: string, provider: string): RegistryModel {
  return { id, label: id, provider, purposes: ["chat"], context_window: null, is_free: null, embed_dim: null }
}

// Echte Lage (30.09.2026): Anthropic ohne Präfix, NVIDIA mit Präfix „nvidia_nim/“.
const catalog: RegistryModel[] = [
  m("claude-a", "anthropic"),
  m("claude-b", "anthropic"),
  m("nvidia_nim/01-ai/yi-large", "nvidia"),
  m("openai-codex/gpt-5.6-sol", "openai-codex"),
  m("openrouter/vendor/x", "openrouter"),
]
const render = (primary = "", selected: string[] = []) =>
  renderToStaticMarkup(
    <FallbackModelsSelector primary={primary} catalog={catalog} selected={selected} onChange={() => {}} />,
  )

describe("FallbackModelsSelector (Task f17cb519)", () => {
  it("zeigt Anzeigenamen der Anbieter statt Präfix", () => {
    const html = render()
    expect(html).toContain("+ Anthropic (2)…")
    expect(html).toContain("+ NVIDIA NIM (1)…")
    expect(html).toContain("+ ChatGPT Plus/Pro (Codex) (1)…")
    expect(html).toContain("+ OpenRouter (1)…")
    expect(html).not.toContain("(direkt)")
    expect(html).not.toContain("+ nvidia_nim")
    expect(html).not.toContain("+ openai-codex")
  })

  it("bietet Hauptmodell und schon gewählte Fallbacks nicht noch einmal an", () => {
    const html = render("claude-a", ["nvidia_nim/01-ai/yi-large"])
    expect(html).toContain("+ Anthropic (1)…")
    expect(html).not.toContain('value="claude-a"')
    expect(html).not.toContain('value="nvidia_nim/01-ai/yi-large"')
    expect(html).not.toContain("NVIDIA NIM")
  })

  it("lässt kein Modell weg", () => {
    const html = render()
    for (const x of catalog) expect(html).toContain(`value="${x.id}"`)
  })

  it("zeigt gewählte Fallbacks in Reihenfolge mit voller id", () => {
    const html = render("", ["openrouter/vendor/x", "claude-b"])
    expect(html.indexOf("openrouter/vendor/x")).toBeLessThan(html.indexOf("claude-b"))
    expect(html).toContain("1.</span>openrouter/vendor/x")
  })
})
