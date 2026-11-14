import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

// Schlüssel statt Text; die Werte der Platzhalter stehen nicht im Schlüssel (Rechnung: templateLogic.test.ts).
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import type { RegistryModel } from "@/features/llm/api"
import { TemplateBudget } from "./TemplateBudget"
import { TemplateChain } from "./TemplateChain"
import { TemplateList } from "./TemplateList"
import { newTemplate } from "./templateLogic"

const m = (id: string, provider: string): RegistryModel =>
  ({ id, label: id, provider, purposes: ["chat"], context_window: null, is_free: null, embed_dim: null })
const models = [m("claude-opus-5-5", "anthropic"), m("openai-codex/gpt-5.6-terra", "openai-codex"),
  m("ollama/gemma4:latest", "ollama")]

describe("TemplateChain", () => {
  it("drei Stufen mit allen Modellen inkl. lokalem Ollama", () => {
    const html = renderToStaticMarkup(
      <TemplateChain chain={["claude-opus-5-5"]} models={models} readOnly={false} onChange={() => {}} />)
    expect(html.match(/<select/g)).toHaveLength(3)
    expect(html).toContain('value="ollama/gemma4:latest"')
  })

  it("warnt bei gleichem Anbieter und unbekanntem Modell", () => {
    const html = renderToStaticMarkup(
      <TemplateChain chain={["claude-opus-5-5", "claude-sonnet-5"]} models={models} readOnly={false} onChange={() => {}} />)
    expect(html).toContain("text-amber-400")
    expect(html).toContain("text-rose-400")
  })

  it("nur lesen: keine Auswahlfelder", () => {
    const html = renderToStaticMarkup(
      <TemplateChain chain={["claude-opus-5-5"]} models={models} readOnly onChange={() => {}} />)
    expect(html).not.toContain("<select")
    expect(html).toContain("claude-opus-5-5")
  })
})

describe("TemplateBudget", () => {
  const t = newTemplate("x")
  it("Überschreitung sichtbar mit berechneter Obergrenze", () => {
    const html = renderToStaticMarkup(
      <TemplateBudget budget={{ ...t.budget, max_iterations: 60, overrun_pct: 20 }} reply={t.reply} readOnly={false}
        onBudget={() => {}} onReply={() => {}} />)
    expect(html).toContain('value="20"')
    expect(html).toContain("templates.budget.overrun_hint")
  })

  it("nur lesen sperrt alle Felder", () => {
    const html = renderToStaticMarkup(
      <TemplateBudget budget={t.budget} reply={t.reply} readOnly onBudget={() => {}} onReply={() => {}} />)
    const inputs = html.match(/<(input|select)[^>]*>/g) ?? []
    expect(inputs.length).toBeGreaterThan(5)
    expect(inputs.every((i) => i.includes("disabled"))).toBe(true)
  })
})

describe("TemplateList", () => {
  it("Gruppen, Ampel und Anzahl", () => {
    const list = [
      { ...newTemplate("buddy"), label: "Buddy", group: "personal" as const, bound_count: 3,
        health: { state: "green" as const, unknown_models: [], same_provider: false, primary_down: false, providers: [] } },
      { ...newTemplate("security"), label: "Security", group: "specialists" as const, bound_count: 1,
        health: { state: "red" as const, unknown_models: ["x"], same_provider: false, primary_down: false, providers: [] } },
    ]
    const html = renderToStaticMarkup(<TemplateList templates={list} selected="buddy" onSelect={() => {}} />)
    expect(html.indexOf("Buddy")).toBeLessThan(html.indexOf("Security"))
    expect(html).toContain("bg-emerald-400")
    expect(html).toContain("bg-rose-500")
    expect(html).toContain(">3<")
  })
})
