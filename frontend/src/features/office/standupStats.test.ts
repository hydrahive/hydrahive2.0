import { describe, expect, it } from "vitest"
import type { ActivityEntry } from "@/features/chat/api"
import { standupStats } from "./standupStats"

function agent(over: Partial<ActivityEntry>): ActivityEntry {
  return { session_id: "s", agent_id: "a", name: "A", project_id: null, current_tool: null, ...over }
}

describe("standupStats (Spec agent-office.md §8.1)", () => {
  it("zählt laufend, Delegationen und Fehler getrennt", () => {
    const stats = standupStats([
      agent({ session_id: "1" }),
      agent({ session_id: "2", parent_session_id: "1" }),
      agent({ session_id: "3", parent_session_id: "1", last_tool_result_summary: "Fehler: x" }),
    ])
    expect(stats).toEqual({ total: 3, delegated: 2, errored: 1 })
  })

  it("leere Liste ergibt alles 0", () => {
    expect(standupStats([])).toEqual({ total: 0, delegated: 0, errored: 0 })
  })

  it("erkennt Fehler nur am Präfix, nicht an jedem Vorkommen des Wortes", () => {
    const stats = standupStats([agent({ last_tool_result_summary: "kein Fehler hier gefunden" })])
    expect(stats.errored).toBe(0)
  })
})
