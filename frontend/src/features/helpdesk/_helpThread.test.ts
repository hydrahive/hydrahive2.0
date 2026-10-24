// Hilfe-Assistent (docs/plans/help-assistant.md): Verlauf aus der Sitzung und aus dem Live-Stream als einfache
// Sprechblasen. Werkzeug-Aufrufe (help_search/help_read) sieht der Nutzer nicht als Text, nur als „sucht im Handbuch“.
import { describe, expect, it } from "vitest"
import { applyHelpEvent, messagesToBubbles, reportIdOf, type HelpBubble } from "./_helpThread"
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

describe("Fehlerbericht im Verlauf (docs/plans/help-error-report.md)", () => {
  const ok = (id: string) => ({ type: "tool_use_result" as const, call_id: "c", tool_name: "error_report_prepare",
    success: true, output: { report_id: id, subject: "[HydraHive-Fehler] X" }, error: null, duration_ms: 3 })

  it("live: Werkzeug-Ergebnis legt eine Bericht-Karte an, der Antworttext folgt danach", () => {
    let b = applyHelpEvent([], { type: "tool_use_start", call_id: "c", tool_name: "error_report_prepare", arguments: {} })
    b = applyHelpEvent(b, ok("Rep-0000001"))
    b = applyHelpEvent(b, { type: "text_delta", text: "Bitte prüfen und senden." })
    expect(b.filter((x) => x.role === "report").map((x) => x.reportId)).toEqual(["Rep-0000001"])
    expect(b.at(-1)?.text).toBe("Bitte prüfen und senden.")
  })

  it("live: fehlgeschlagenes oder fremdes Werkzeug ergibt keine Karte", () => {
    const failed = { ...ok("Rep-0000002"), success: false, output: null, error: "aus" }
    expect(applyHelpEvent([], failed).some((x) => x.role === "report")).toBe(false)
    expect(applyHelpEvent([], { ...ok("Rep-0000003"), tool_name: "help_read" }).some((x) => x.role === "report")).toBe(false)
  })

  it("Verlauf: Karte aus dem gespeicherten Werkzeug-Ergebnis", () => {
    const b = messagesToBubbles([
      msg("1", "user", "Senden geht nicht"),
      msg("2", "assistant", [{ type: "tool_use", id: "t1", name: "error_report_prepare", input: { description: "x" } }]),
      msg("3", "tool", [{ type: "tool_result", tool_use_id: "t1", content: JSON.stringify({ report_id: "Rep-0000009", subject: "s" }) }]),
      msg("4", "assistant", [{ type: "text", text: "Liegt im Fenster." }]),
    ])
    expect(b.map((x) => [x.role, x.reportId ?? x.text])).toEqual([
      ["user", "Senden geht nicht"], ["report", "Rep-0000009"], ["assistant", "Liegt im Fenster."],
    ])
  })

  it("nur gültige IDs (16 Zeichen wie token_urlsafe(12), keine Sonderzeichen)", () => {
    expect(reportIdOf({ report_id: "AbC-_123456789xy" })).toBe("AbC-_123456789xy")
    expect(reportIdOf('{"report_id":"AbC-_123456789xy"}')).toBe("AbC-_123456789xy")
    expect(reportIdOf({ report_id: "../../x" })).toBeNull()
    expect(reportIdOf({ report_id: "x" })).toBeNull()
    expect(reportIdOf("kein json")).toBeNull()
  })

  it("Verlauf: kaputtes Ergebnis wird ignoriert", () => {
    const b = messagesToBubbles([
      msg("2", "assistant", [{ type: "tool_use", id: "t1", name: "error_report_prepare", input: {} }]),
      msg("3", "tool", [{ type: "tool_result", tool_use_id: "t1", content: "kein json", is_error: true }]),
    ])
    expect(b).toEqual([])
  })
})

