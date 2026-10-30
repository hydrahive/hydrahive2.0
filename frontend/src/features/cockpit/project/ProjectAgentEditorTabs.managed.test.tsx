import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn(), patch: vi.fn() } }))
import { ProjectAgentEditorTabs } from "./ProjectAgentEditorTabs"
import { activeTabFor } from "@/features/agents/managedAgent"
import type { Agent } from "@/features/agents/types"

const BASE = { id: "a1", type: "specialist", name: "Labor-Agent", owner: "admin", created_by: "admin", llm_model: "m",
  fallback_models: [], tools: ["shell_exec"], mcp_servers: [], description: "", temperature: 0.7, max_tokens: 1000,
  thinking_budget: 0, status: "active", created_at: "", updated_at: "", project_id: "p1" } as unknown as Agent

const render = (a: Agent) => renderToStaticMarkup(<ProjectAgentEditorTabs agent={a} draft={a} prompt="" models={[]} catalog={[]}
  tools={[]} mcpServers={[]} onChange={() => {}} onPromptChange={() => {}} soulActive={false} onSoulSaved={() => {}} />)

describe("Projekt-Agent bearbeiten – verwaltet", () => {
  it("verwaltet: Hinweis mit Modulname, keine Reiter für Prompt, Tools, Skills, Soul", () => {
    const html = render({ ...BASE, managed_by: "hydralabor" })
    expect(html).toContain('managed.hint:{&quot;module&quot;:&quot;hydralabor&quot;}')
    for (const k of ["fields.system_prompt", ">Tools<", ">Skills<", "tabs.soul", ">Erweitert<"]) expect(html).not.toContain(k)
    for (const k of ["Übersicht", "Modell", "Intervalle"]) expect(html).toContain(k)
  })

  it("normal: alle Reiter, kein Hinweis", () => {
    const html = render(BASE)
    expect(html).not.toContain("managed.hint")
    for (const k of ["fields.system_prompt", ">Tools<", ">Skills<", "tabs.soul"]) expect(html).toContain(k)
  })
})

describe("Projekt-Agent bearbeiten – Reiter-Zustand", () => {
  it("ein offener Reiter, der nicht (mehr) angeboten wird, fällt auf Übersicht zurück", () => {
    const tabs = [{ id: "overview" }, { id: "model" }, { id: "schedules" }]
    expect(activeTabFor("tools", tabs, true)).toBe("overview")
    expect(activeTabFor("model", tabs, true)).toBe("model")
    expect(activeTabFor("mail", [...tabs, { id: "mail" }], false)).toBe("overview")
    expect(activeTabFor("mail", [...tabs, { id: "mail" }], true)).toBe("mail")
  })
})
