// Hilfe-Assistent (docs/plans/help-assistant.md): Verlauf aus der Sitzung und aus dem Live-Stream als einfache
// Sprechblasen. Werkzeug-Aufrufe (help_search/help_read) sieht der Nutzer nicht als Text, nur als „sucht im Handbuch“.
import { describe, expect, it } from "vitest"
import { applyHelpEvent, messagesToBubbles, type HelpBubble } from "./_helpThread"
import type { Message } from "@/features/chat/types"

const msg = (id: string, role: Message["role"], content: Message["content"]): Message => ({
  id, role, content, created_at: "", token_count: null, metadata: {},
})

describe("messagesToBubbles", () => {
  it("zeigt Nutzer- und Antworttexte in Reihenfolge", () => {
    const b = messagesToBubbles([
      msg("1", "user", "Wie lege ich einen Agenten an?"),
      msg("2", "assistant", [{ type: "text", text: "Unter Agenten → Neu." }]),
    ])
    expect(b).toEqual([
      { id: "1", role: "user", text: "Wie lege ich einen Agenten an?" },
      { id: "2", role: "assistant", text: "Unter Agenten → Neu." },
    ])
  })

  it("aus dem Verlauf nur den Text nach dem letzten Werkzeug-Aufruf", () => {
    const b = messagesToBubbles([
      msg("2", "assistant", [
        { type: "text", text: "Ich schaue nach." },
        { type: "tool_use", id: "t", name: "help_read", input: { topic: "agents" } },
        { type: "text", text: "So geht es." },
      ]),
    ])
    expect(b).toEqual([{ id: "2", role: "assistant", text: "So geht es." }])
  })

  it("lässt Werkzeug-Aufrufe und -Ergebnisse weg, nimmt nur den Text der Antwort", () => {
    const b = messagesToBubbles([
      msg("2", "assistant", [
        { type: "tool_use", id: "t", name: "help_search", input: { query: "Agent" } },
        { type: "text", text: "Hier steht es." },
      ]),
      msg("3", "tool", [{ type: "tool_result", tool_use_id: "t", content: "{...}" }]),
    ])
    expect(b).toEqual([{ id: "2", role: "assistant", text: "Hier steht es." }])
  })

  it("überspringt leere und System-Nachrichten", () => {
    expect(messagesToBubbles([msg("1", "system", "x"), msg("2", "assistant", []), msg("3", "compaction", "y")]))
      .toEqual([])
  })
})

describe("applyHelpEvent", () => {
  const start: HelpBubble[] = [{ id: "u", role: "user", text: "Frage" }]

  it("legt beim ersten Text eine Antwortblase an und hängt Deltas an", () => {
    let b = applyHelpEvent(start, { type: "text_delta", text: "Hal" })
    b = applyHelpEvent(b, { type: "text_delta", text: "lo" })
    expect(b.at(-1)).toEqual({ id: "live", role: "assistant", text: "Hallo", busy: undefined })
  })

  it("zeigt „sucht im Handbuch“ während eines Werkzeug-Aufrufs", () => {
    const b = applyHelpEvent(start, { type: "tool_use_start", call_id: "c", tool_name: "help_search", arguments: {} })
    expect(b.at(-1)).toMatchObject({ id: "live", role: "assistant", busy: "search" })
  })

  it("Text vor einem Werkzeug-Aufruf wird verworfen – nur die eigentliche Antwort bleibt (Live-Befund 23.10.2026)", () => {
    let b = applyHelpEvent(start, { type: "text_delta", text: "Ich schaue kurz nach." })
    b = applyHelpEvent(b, { type: "tool_use_start", call_id: "c", tool_name: "help_read", arguments: {} })
    b = applyHelpEvent(b, { type: "text_delta", text: "Auf Einstellungen → Agenten …" })
    expect(b.at(-1)?.text).toBe("Auf Einstellungen → Agenten …")
  })

  it("Fehler im Lauf wird als Fehlerblase gezeigt", () => {
    const b = applyHelpEvent(start, { type: "error", message: "Modell nicht erreichbar", fatal: true })
    expect(b.at(-1)).toEqual({ id: "live", role: "error", text: "Modell nicht erreichbar" })
  })

  it("done beendet die Live-Blase (feste ID, kein busy mehr)", () => {
    let b = applyHelpEvent(start, { type: "text_delta", text: "Fertig" })
    b = applyHelpEvent(b, { type: "done", message_id: "m9", iterations: 1, input_tokens: 0, output_tokens: 0,
      cache_creation_tokens: 0, cache_read_tokens: 0 })
    expect(b.at(-1)).toEqual({ id: "m9", role: "assistant", text: "Fertig" })
  })

  it("ändert die übergebene Liste nicht", () => {
    const before = JSON.stringify(start)
    applyHelpEvent(start, { type: "text_delta", text: "x" })
    expect(JSON.stringify(start)).toBe(before)
  })
})
