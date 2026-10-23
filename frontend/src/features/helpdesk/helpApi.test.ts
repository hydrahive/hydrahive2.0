// Hilfe-Assistent: Senden an /api/helpdesk/messages (mit aktueller Seite) und Lesen des SSE-Streams.
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "TOK" }) } }))
import { readOpen, sendHelpMessage, writeOpen } from "./helpApi"

function sse(...events: object[]): Response {
  const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("")
  return new Response(new Blob([body]).stream(), { status: 200 })
}

describe("sendHelpMessage", () => {
  beforeEach(() => vi.restoreAllMocks())

  it("schickt Sitzung, Text und aktuellen Pfad mit Anmeldung und liefert die Ereignisse", async () => {
    const fetchMock = vi.fn().mockResolvedValue(sse({ type: "text_delta", text: "Hi" }, { type: "done", message_id: "m" }))
    vi.stubGlobal("fetch", fetchMock)
    const got = []
    for await (const ev of sendHelpMessage("s1", "Frage", "/containers")) got.push(ev)
    expect(got.map((e) => e.type)).toEqual(["text_delta", "done"])
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe("/api/helpdesk/messages")
    expect(init.method).toBe("POST")
    expect(init.headers.Authorization).toBe("Bearer TOK")
    expect(JSON.parse(init.body)).toEqual({ session_id: "s1", text: "Frage", path: "/containers" })
  })

  it("Fehler vom Server → Fehler mit Code", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: { code: "helpdesk_model_missing" } }), { status: 409 })))
    await expect(async () => { for await (const _ of sendHelpMessage("s", "x", "/")) void _ }).rejects
      .toMatchObject({ code: "helpdesk_model_missing" })
  })
})

describe("Fenster offen merken", () => {
  const mem = new Map<string, string>()
  beforeEach(() => {
    mem.clear()
    Object.defineProperty(globalThis, "sessionStorage", { configurable: true, value: {
      getItem: (k: string) => mem.get(k) ?? null, setItem: (k: string, v: string) => { mem.set(k, v) },
    } })
  })

  it("ist zu, solange nichts gemerkt ist, und merkt sich offen/zu", () => {
    expect(readOpen()).toBe(false)
    writeOpen(true)
    expect(readOpen()).toBe(true)
    writeOpen(false)
    expect(readOpen()).toBe(false)
  })
})
