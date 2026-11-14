import { describe, expect, it, vi } from "vitest"

const get = vi.fn(async (_url: string) => ({ session_id: "s1", calls: [] }))
vi.mock("@/shared/api-client", () => ({ api: { get: (url: string) => get(url) } }))

import { fetchAgentTrace } from "./api"

describe("fetchAgentTrace", () => {
  it("ruft die Trace-Route der Session ab (Spec agent-office.md §2)", async () => {
    await fetchAgentTrace("sess-42")
    expect(get).toHaveBeenCalledWith("/agents/activity/sess-42/trace")
  })
})
