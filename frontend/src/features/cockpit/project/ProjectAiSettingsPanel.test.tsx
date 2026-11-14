import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/features/llm/templates/api", () => ({ templatesApi: { list: () => new Promise(() => {}) } }))
vi.mock("@/features/agents/api", () => ({ agentsApi: { update: vi.fn() } }))
import { ProjectAiSettingsPanel } from "./ProjectAiSettingsPanel"

const agents = [{ id: "a", name: "P", type: "project", llm_model: "claude-opus-5-5", status: "active", template: "projekt-master" }]

describe("Projekt-KI-Einstellungen (Aufräumen 14.11.2026)", () => {
  it("zeigt nur die Template-Auswahl, kein Modell- oder Denktiefe-Feld", () => {
    const html = renderToStaticMarkup(<ProjectAiSettingsPanel agentId="a" agents={agents} onAgentChanged={() => {}} />)
    expect(html).toContain("template.label")
    expect(html).not.toContain("project-ai-model")
    expect(html).not.toContain("Thinking-Tiefe")
  })
})
