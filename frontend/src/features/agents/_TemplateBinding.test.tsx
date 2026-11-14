import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/features/llm/templates/api", () => ({ templatesApi: { list: () => new Promise(() => {}) } }))
vi.mock("@/features/llm/api", () => ({}))
import { ModelTab } from "./_ModelTab"
import { TemplateSummary } from "./_TemplateBinding"
import type { Agent } from "./types"
import { newTemplate } from "@/features/llm/templates/templateLogic"

const agent = (template?: string) => ({
  id: "a", type: "specialist", name: "x", owner: "u", created_by: "u", llm_model: "claude-sonnet-5",
  fallback_models: [], tools: [], mcp_servers: [], description: "", temperature: 0.7, max_tokens: 1000,
  thinking_budget: 0, status: "active", created_at: "", updated_at: "", template,
}) as Agent

describe("Agent-Editor mit Template (Plan E3)", () => {
  it("gebunden: keine Felder für Modell, Fallback, Budget – nur Temperatur", () => {
    const html = renderToStaticMarkup(<ModelTab draft={agent("reviewer")} catalog={[]} onChange={() => {}} />)
    expect(html).toContain("template.label")
    expect(html).not.toContain("fields.fallback_models")
    expect(html).not.toContain("fields.max_tokens")
    expect(html).toContain("fields.temperature")
  })

  it("ungebunden: keine alten Felder mehr, Aufforderung ein Template zu wählen (Aufräumen 14.11.2026)", () => {
    const html = renderToStaticMarkup(<ModelTab draft={agent()} catalog={[]} onChange={() => {}} />)
    expect(html).not.toContain("fields.fallback_models")
    expect(html).not.toContain("fields.model")
    expect(html).toContain("template.unbound_required")
  })

  it("Zusammenfassung zeigt die Kette", () => {
    const html = renderToStaticMarkup(<TemplateSummary tpl={{ ...newTemplate("r"), chain: ["a", "b"] }} />)
    expect(html).toContain("a → b")
  })
})
