import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import type { RegistryModel } from "@/features/llm/api"
import { AgentModelPicker } from "./_AgentModelPicker"

function m(id: string, provider: string): RegistryModel {
  return { id, label: id, provider, purposes: ["chat"], context_window: null, is_free: null, embed_dim: null }
}

// 150 Modelle vor den Anbietern, die früher abgeschnitten wurden.
const catalog: RegistryModel[] = [
  ...Array.from({ length: 150 }, (_, i) => m(`nvidia/model-${i}`, "nvidia")),
  m("openai-codex/gpt-5.6-sol", "openai-codex"),
  m("openrouter/vendor/letztes", "openrouter"),
]
const render = (value = "") =>
  renderToStaticMarkup(<AgentModelPicker value={value} catalog={catalog} onChange={() => {}} />)

describe("AgentModelPicker", () => {
  it("rendert alle Modelle als Option, auch hinter Position 100 (Task 19687316)", () => {
    const html = render()
    expect(html).toContain('value="openai-codex/gpt-5.6-sol"')
    expect(html).toContain('value="openrouter/vendor/letztes"')
    expect(html.match(/<option value="nvidia\/model-/g)).toHaveLength(150)
  })

  it("gruppiert nach Anbieter mit Anzeigename und Anzahl", () => {
    const html = render()
    expect(html).toContain('<optgroup label="NVIDIA NIM (150)">')
    expect(html).toContain('<optgroup label="ChatGPT Plus/Pro (Codex) (1)">')
  })

  it("bietet jeden Anbieter im Filter an", () => {
    const html = render()
    expect(html).toContain('<option value="openrouter">OpenRouter (1)</option>')
    expect(html).toContain('<option value="openai-codex">ChatGPT Plus/Pro (Codex) (1)</option>')
  })

  it("zeigt ein gespeichertes Modell, das nicht im Katalog ist, als aktuell", () => {
    expect(render("alt/verschwunden")).toContain('value="alt/verschwunden"')
  })
})
