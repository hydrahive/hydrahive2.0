import { describe, expect, it, vi } from "vitest"
import { runSseLoop } from "./_sseLoop"

function sse(...frames: string[]): Response {
  const body = new ReadableStream<Uint8Array>({
    start(c) {
      for (const f of frames) c.enqueue(new TextEncoder().encode(f))
      c.close()
    },
  })
  return new Response(body, { status: 200 })
}

const noWait = () => Promise.resolve()

describe("runSseLoop", () => {
  it("meldet sich bei 401 ab und beendet die Schleife (Task a7477846)", async () => {
    const fetchFn = vi.fn(async () => new Response("", { status: 401 }))
    const onUnauthorized = vi.fn()
    const signal = new AbortController().signal
    await runSseLoop({ url: "/x", token: () => "t", onFrame: () => {}, onUnauthorized, signal, fetchFn, wait: noWait })
    expect(fetchFn).toHaveBeenCalledTimes(1)
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })

  it("verbindet nach anderen Fehlern neu, bis abgebrochen wird", async () => {
    const ctrl = new AbortController()
    let calls = 0
    const fetchFn = vi.fn(async () => {
      calls += 1
      if (calls === 3) ctrl.abort()
      return new Response("", { status: 503 })
    })
    const onUnauthorized = vi.fn()
    await runSseLoop({ url: "/x", token: () => null, onFrame: () => {}, onUnauthorized, signal: ctrl.signal, fetchFn, wait: noWait })
    expect(calls).toBe(3)
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it("wartet zwischen den Versuchen länger (Backoff, gedeckelt)", async () => {
    const ctrl = new AbortController()
    const waits: number[] = []
    const fetchFn = vi.fn(async () => {
      if (waits.length >= 6) ctrl.abort()
      return new Response("", { status: 500 })
    })
    const wait = async (ms: number) => { waits.push(ms) }
    await runSseLoop({ url: "/x", token: () => null, onFrame: () => {}, onUnauthorized: () => {}, signal: ctrl.signal, fetchFn, wait })
    expect(waits[0]).toBe(1500)
    expect(waits[1]).toBeGreaterThan(waits[0])
    expect(Math.max(...waits)).toBeLessThanOrEqual(30000)
  })

  it("setzt den Backoff nach einer erfolgreichen Verbindung zurück", async () => {
    const ctrl = new AbortController()
    const waits: number[] = []
    const replies = [500, 500, 200, 500]
    const fetchFn = vi.fn(async () => {
      const status = replies.shift()
      if (status === undefined) { ctrl.abort(); return new Response("", { status: 500 }) }
      return status === 200 ? sse("data: 1\n\n") : new Response("", { status })
    })
    await runSseLoop({ url: "/x", token: () => null, onFrame: () => {}, onUnauthorized: () => {}, signal: ctrl.signal, fetchFn, wait: async (ms) => { waits.push(ms) } })
    // 500 → 1500, 500 → >1500, 200 (Stream endet) → Reset → 1500, 500 → >1500
    expect(waits[2]).toBe(1500)
  })

  it("liefert ganze Frames, auch über Chunk-Grenzen, und sendet den Token", async () => {
    const ctrl = new AbortController()
    const frames: string[] = []
    let seenAuth: string | null = null
    const fetchFn = vi.fn(async (_url: string, init?: RequestInit) => {
      seenAuth = new Headers(init?.headers).get("Authorization")
      ctrl.abort()
      return sse(": keepalive\n\n", "data: {\"a\"", ":1}\n\n")
    })
    await runSseLoop({ url: "/x", token: () => "abc", onFrame: (f) => frames.push(f), onUnauthorized: () => {}, signal: ctrl.signal, fetchFn, wait: noWait })
    expect(seenAuth).toBe("Bearer abc")
    expect(frames).toEqual([": keepalive", "data: {\"a\":1}"])
  })
})
