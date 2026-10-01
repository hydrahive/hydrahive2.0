import { afterEach, describe, expect, it, vi } from "vitest"
import type { ChatState } from "./useChat"

const runStatus = vi.fn()
const attachRun = vi.fn()
vi.mock("./api", () => ({ chatApi: { runStatus: (...a: unknown[]) => runStatus(...a) }, attachRun: (...a: unknown[]) => attachRun(...a) }))

vi.mock("@/shared/runFinished", () => ({ notifyRunFinished: () => {} }))

const { followRun, pingKind } = await import("./_runFollow")

function deps(over: Partial<{ busy: boolean; running: boolean }> = {}) {
  let state = { messages: [], loadedFor: "s1", busy: false, compacting: false, iteration: 0,
    error: null, errorKind: null, pendingConfirm: null, lastTurnTokens: null } as ChatState
  const setState = (u: ChatState | ((s: ChatState) => ChatState)) => { state = typeof u === "function" ? u(state) : u }
  const reload = vi.fn(async () => {})
  return {
    d: {
      sessionId: "s1", controller: new AbortController(), setState: setState as never, reload,
      runningRef: { current: over.running ?? false }, busyRef: { current: over.busy ?? false },
      abortRef: { current: null as AbortController | null },
    },
    get state() { return state },
    reload,
  }
}

async function* events(evs: Record<string, unknown>[]) { for (const e of evs) yield e }

afterEach(() => { runStatus.mockReset(); attachRun.mockReset() })

describe("pingKind", () => {
  it("liest den Typ aus data-Frames, ignoriert Keepalives", () => {
    expect(pingKind('data: {"t":"start"}')).toBe("start")
    expect(pingKind(": keepalive")).toBeNull()
    expect(pingKind("data: kaputt")).toBe("")
  })
})

describe("followRun", () => {
  it("Start-Ping: lädt nach, streamt ab Puffer-Anfang in einen Platzhalter, gibt danach frei", async () => {
    runStatus.mockResolvedValue({ running: true, latest_seq: 7 })
    attachRun.mockReturnValue(events([
      { type: "message_start" }, { type: "text_delta", text: "Hallo" },
      { type: "done", input_tokens: 1, output_tokens: 1, cache_creation_tokens: 0, cache_read_tokens: 0 },
    ]))
    const t = deps()
    await followRun(t.d, true)
    expect(attachRun.mock.calls[0][1]).toBe(0)
    expect(t.reload).toHaveBeenCalledTimes(2)  // vorher (Auslöser) + nachher (Endstand)
    const live = t.state.messages.find((m) => m.id.startsWith("live-"))
    expect(live?.content).toEqual([{ type: "text", text: "Hallo" }])
    expect(t.d.runningRef.current).toBe(false)
    expect(t.state.busy).toBe(false)
  })

  it("Abbruch im Stream: Stopp-Knopf wird trotzdem frei", async () => {
    runStatus.mockResolvedValue({ running: true, latest_seq: 0 })
    attachRun.mockImplementation(async function* () { yield { type: "message_start" }; throw new Error("weg") })
    const t = deps()
    await followRun(t.d, true)
    expect(t.state.busy).toBe(false)
    expect(t.d.runningRef.current).toBe(false)
  })

  it("Reconnect: ab latest_seq, kein Platzhalter", async () => {
    runStatus.mockResolvedValue({ running: true, latest_seq: 7 })
    attachRun.mockReturnValue(events([]))
    const t = deps()
    await followRun(t.d, false)
    expect(attachRun.mock.calls[0][1]).toBe(7)
    expect(t.state.messages).toEqual([])
  })

  it("hängt sich nicht doppelt an und stört den eigenen Sende-Stream nicht", async () => {
    runStatus.mockResolvedValue({ running: true, latest_seq: 1 })
    for (const over of [{ busy: true }, { running: true }]) {
      const t = deps(over)
      await followRun(t.d, true)
      expect(attachRun).not.toHaveBeenCalled()
      expect(t.reload).not.toHaveBeenCalled()
    }
  })

  it("nichts läuft → nichts tun", async () => {
    runStatus.mockResolvedValue({ running: false, latest_seq: 0 })
    const t = deps()
    await followRun(t.d, true)
    expect(attachRun).not.toHaveBeenCalled()
    expect(t.state.busy).toBe(false)
  })
})
