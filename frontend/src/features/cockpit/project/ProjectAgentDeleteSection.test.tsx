import { renderToStaticMarkup } from "react-dom/server"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { Agent } from "@/features/agents/types"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/features/archive/delete/DeleteDialog", () => ({ DeleteDialog: () => null }))

const auth = vi.hoisted(() => ({ role: null as string | null }))
vi.mock("@/features/auth/useAuthStore", () => ({
  useAuthStore: <T,>(selector: (state: typeof auth) => T) => selector(auth),
}))

import { ProjectAgentDeleteSection } from "./ProjectAgentDeleteSection"

const BASE = { id: "a1", name: "Spezi", owner: "admin", created_by: "admin", llm_model: "m",
  fallback_models: [], tools: [], mcp_servers: [], description: "", temperature: 0.7, max_tokens: 1000,
  thinking_budget: 0, status: "active", created_at: "", updated_at: "", project_id: "p1" }

afterEach(() => { auth.role = null })

const render = (agent: Agent) => renderToStaticMarkup(
  <ProjectAgentDeleteSection agent={agent} onDeleted={() => {}} onDeleteStarted={() => {}} />,
)

describe("ProjectAgentDeleteSection", () => {
  it("Admin + Spezialist: Abschnitt mit Lösch-Knopf sichtbar", () => {
    auth.role = "admin"
    const html = render({ ...BASE, type: "specialist" } as Agent)
    expect(html).toContain("delete_specialist.title")
    expect(html).toContain("delete_specialist.button")
  })

  it("Projekt-Agent (Lead): kein Abschnitt, auch als Admin nicht", () => {
    auth.role = "admin"
    const html = render({ ...BASE, type: "project" } as Agent)
    expect(html).toBe("")
  })

  it("Spezialist ohne Admin-Rolle: kein Abschnitt", () => {
    auth.role = "user"
    const html = render({ ...BASE, type: "specialist" } as Agent)
    expect(html).toBe("")
  })

  it("Spezialist ohne Rolle (nicht geladen): kein Abschnitt", () => {
    const html = render({ ...BASE, type: "specialist" } as Agent)
    expect(html).toBe("")
  })
})
