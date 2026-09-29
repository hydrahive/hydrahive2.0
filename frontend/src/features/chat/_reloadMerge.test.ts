import { describe, expect, it } from "vitest"
import { applyReload, type LoadedThread } from "./_reloadMerge"
import type { Message } from "./types"

function msg(id: string, role: Message["role"], text: string): Message {
  return { id, role, content: text, created_at: "2026-09-29T10:00:00Z", token_count: null, metadata: {} }
}

const old = msg("db-0", "user", "alt")
// Direkt nach dem Absenden: lokale User-Nachricht + Live-Antwort (noch ohne DB-ID).
const sending: LoadedThread = {
  loadedFor: "A",
  messages: [old, msg("local-1", "user", "frage"), msg("live-1", "assistant", "antwort")],
}
// Serverstand nach dem Lauf: dieselben Nachrichten, jetzt mit echten DB-IDs.
const persisted = [old, msg("db-u1", "user", "frage"), msg("db-a1", "assistant", "antwort")]
const otherSession = [msg("b-1", "user", "andere Session")]

describe("applyReload", () => {
  it("behält die abgeschickte Nachricht, solange der Lauf läuft und der Server sie noch nicht kennt (#437)", () => {
    const out = applyReload(sending, "A", [old], true)
    expect(out.messages.map((m) => m.id)).toEqual(["db-0", "local-1", "live-1"])
    expect(out.loadedFor).toBe("A")
  })

  it("zeigt nach Laufende jede Nachricht genau einmal", () => {
    const out = applyReload(sending, "A", persisted, false)
    expect(out.messages).toEqual(persisted)
  })

  it("doppelt auch über zwei Läufe im selben Tab nichts", () => {
    const afterRun1 = applyReload(sending, "A", persisted, false)
    const sending2: LoadedThread = {
      ...afterRun1,
      messages: [...afterRun1.messages, msg("local-2", "user", "frage2"), msg("live-2", "assistant", "antwort2")],
    }
    const persisted2 = [...persisted, msg("db-u2", "user", "frage2"), msg("db-a2", "assistant", "antwort2")]
    expect(applyReload(sending2, "A", persisted2, false).messages).toEqual(persisted2)
  })

  it("nimmt beim Session-Wechsel keine Platzhalter in die neue Session mit", () => {
    const out = applyReload(sending, "B", otherSession, false)
    expect(out.messages).toEqual(otherSession)
    expect(out.loadedFor).toBe("B")
  })

  it("nimmt auch während eines Laufs keine Platzhalter in eine andere Session mit", () => {
    expect(applyReload(sending, "B", otherSession, true).messages).toEqual(otherSession)
  })
})
