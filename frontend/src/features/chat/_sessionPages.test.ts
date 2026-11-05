import { describe, expect, it } from "vitest"
import { mergeSessionPages, sessionMatchesScope } from "./_sessionPages"
import type { Session } from "./types"

function session(id: string, updated_at: string): Session {
  return {
    id, agent_id: "agent", user_id: "user", project_id: null, title: id,
    status: "active", created_at: updated_at, updated_at, metadata: {},
  }
}

describe("mergeSessionPages", () => {
  it("ergänzt Seiten in der Server-Sortierung", () => {
    const result = mergeSessionPages(
      [session("older", "2025-01-01T00:00:00Z")],
      [session("newer", "2025-02-01T00:00:00Z")],
    )

    expect(result.map((item) => item.id)).toEqual(["newer", "older"])
  })

  it("dedupliziert IDs und übernimmt die frischere Session-Version", () => {
    const result = mergeSessionPages(
      [session("same", "2025-01-01T00:00:00Z"), session("other", "2025-01-01T00:00:00Z")],
      [session("same", "2025-03-01T00:00:00Z")],
    )

    expect(result.map((item) => item.id)).toEqual(["same", "other"])
    expect(result[0].updated_at).toBe("2025-03-01T00:00:00Z")
  })

  it("verwendet die ID als stabilen Tie-Breaker", () => {
    const result = mergeSessionPages([], [
      session("a", "2025-01-01T00:00:00Z"),
      session("b", "2025-01-01T00:00:00Z"),
    ])

    expect(result.map((item) => item.id)).toEqual(["b", "a"])
  })
})

describe("sessionMatchesScope", () => {
  const item = session("s", "2025-01-01T00:00:00Z")

  it("unterscheidet alle, unzugeordnete und konkrete Projekt-Sessions", () => {
    expect(sessionMatchesScope(item, undefined)).toBe(true)
    expect(sessionMatchesScope(item, null)).toBe(true)
    expect(sessionMatchesScope({ ...item, project_id: "p1" }, "p1")).toBe(true)
    expect(sessionMatchesScope({ ...item, project_id: "p2" }, "p1")).toBe(false)
  })
})
