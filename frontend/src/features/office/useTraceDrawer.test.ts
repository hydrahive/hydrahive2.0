import { describe, expect, it, vi } from "vitest"
vi.mock("./api", () => ({ fetchAgentTrace: vi.fn() }))
import { drawerReducer, initialDrawerState } from "./useTraceDrawer"

describe("drawerReducer (Spec agent-office.md §4.2: Drawer öffnen/schließen)", () => {
  it("startet geschlossen", () => {
    expect(initialDrawerState.openSessionId).toBeNull()
    expect(initialDrawerState.calls).toEqual([])
  })

  it("open setzt die Session und leert alte Calls (Ladezustand)", () => {
    const s = drawerReducer(initialDrawerState, { type: "open", sessionId: "s1" })
    expect(s.openSessionId).toBe("s1")
    expect(s.calls).toEqual([])
  })

  it("loaded füllt die Calls nur, wenn die Session noch die geöffnete ist (keine Race)", () => {
    const opened = drawerReducer(initialDrawerState, { type: "open", sessionId: "s1" })
    const loaded = drawerReducer(opened, { type: "loaded", sessionId: "s1", calls: [{ id: "c1", tool_name: "x", status: "success", duration_ms: 1, created_at: "", iteration: 1 }] })
    expect(loaded.calls).toHaveLength(1)
    // Antwort für eine inzwischen verlassene Session kommt verspätet an -> ignorieren
    const stale = drawerReducer(loaded, { type: "loaded", sessionId: "s0", calls: [{ id: "x", tool_name: "y", status: "success", duration_ms: 1, created_at: "", iteration: 1 }] })
    expect(stale.calls).toHaveLength(1)
    expect(stale.calls[0].id).toBe("c1")
  })

  it("close räumt alles leer", () => {
    const opened = drawerReducer(initialDrawerState, { type: "open", sessionId: "s1" })
    const closed = drawerReducer(opened, { type: "close" })
    expect(closed.openSessionId).toBeNull()
    expect(closed.calls).toEqual([])
  })
})
