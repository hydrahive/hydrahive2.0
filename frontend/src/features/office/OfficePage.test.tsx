// Spec docs/specs/agent-office.md §4: Seite /office, Etappe 2 (ohne Grafik — Karten + Drawer).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import type { ActivityEntry } from "@/features/chat/api"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o?.defaultValue as string) ?? k }) }))

let running: ActivityEntry[] = []
vi.mock("@/features/chat/useAgentActivity", () => ({
  useAgentActivity: () => ({ running, doneNames: [] }),
}))
vi.mock("./api", () => ({ fetchAgentTrace: vi.fn(async () => ({ session_id: "s1", calls: [] })) }))

import { OfficePage } from "./OfficePage"

const html = () => renderToStaticMarkup(<OfficePage />)

describe("OfficePage", () => {
  it("zeigt den Leerzustand, wenn niemand arbeitet", () => {
    running = []
    expect(html()).toMatch(/Gerade arbeitet niemand/)
  })

  it("zeigt eine Karte je laufendem Agenten mit Namen, Projekt und Kurzfassung", () => {
    running = [
      { session_id: "s1", agent_id: "a1", name: "Reviewer", project_id: "P1", current_tool: "shell_exec",
        last_tool_result_summary: "Tests laufen", iteration: 3, max_iterations: 40 },
    ]
    const h = html()
    expect(h).toContain("Reviewer")
    expect(h).toContain("Tests laufen")
  })

  it("jede Karte ist klickbar (öffnet den Drawer) und trägt die session_id", () => {
    running = [
      { session_id: "s1", agent_id: "a1", name: "Reviewer", project_id: "P1", current_tool: "shell_exec" },
    ]
    const h = html()
    expect(h).toMatch(/data-agent-card="s1"[^>]*type="button"|type="button"[^>]*data-agent-card="s1"/)
  })

  it("zeigt die Verbindung zum Auftraggeber, wenn parent_session_id gesetzt ist", () => {
    running = [
      { session_id: "s1", agent_id: "a1", name: "Buddy", project_id: null, current_tool: null },
      { session_id: "s2", agent_id: "a2", name: "Specialist", project_id: "P1", current_tool: "ask_agent",
        parent_session_id: "s1" },
    ]
    const h = html()
    expect(h).toContain('data-parent="s1"')
  })
})
