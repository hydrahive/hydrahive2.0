// Hilfe-Assistent (docs/plans/help-assistant.md): Verlauf als einfache Sprechblasen.
// Werkzeug-Aufrufe (help_search/help_read, später open_page) erscheinen nicht als Text – nur als Hinweis
// „sucht im Handbuch“, solange sie laufen. Reine Funktionen, ohne React – testbar.
import type { ContentBlock, Message, RunnerEvent } from "@/features/chat/types"

export type HelpBusy = "search" | "read" | "think"

export interface HelpBubble {
  id: string
  role: "user" | "assistant" | "error" | "report"
  text: string
  busy?: HelpBusy
  /** role "report": Entwurf eines Fehlerberichts (docs/plans/help-error-report.md) – die Karte lädt ihn selbst. */
  reportId?: string
}

export const REPORT_TOOL = "error_report_prepare"

/** report_id aus dem Ergebnis von error_report_prepare (Objekt live, JSON-Text im Verlauf) – sonst null. */
export function reportIdOf(output: unknown): string | null {
  let o = output
  if (typeof o === "string") { try { o = JSON.parse(o) } catch { return null } }
  const id = (o as { report_id?: unknown } | null)?.report_id
  return typeof id === "string" && /^[A-Za-z0-9_-]{6,64}$/.test(id) ? id : null
}

const reportBubble = (id: string): HelpBubble => ({ id: `report-${id}`, role: "report", text: "", reportId: id })

const LIVE = "live"

/** Antworttext ohne Vorrede: nur der Text nach dem letzten Werkzeug-Aufruf („Ich schaue kurz nach.“ vor der Suche
 *  klebte sonst vor der eigentlichen Antwort – Live-Befund 23.10.2026). */
function textOf(content: Message["content"]): string {
  if (typeof content === "string") return content
  if (!Array.isArray(content)) return ""
  const lastTool = content.map((b) => b.type).lastIndexOf("tool_use")
  return content
    .slice(lastTool + 1)
    .filter((b): b is Extract<ContentBlock, { type: "text" }> => b.type === "text")
    .map((b) => b.text)
    .join("")
    .trim()
}

export function messagesToBubbles(messages: Message[]): HelpBubble[] {
  const out: HelpBubble[] = []
  const reportCalls = new Set<string>()
  for (const m of messages) {
    if (Array.isArray(m.content)) {
      for (const b of m.content) {
        if (b.type === "tool_use" && b.name === REPORT_TOOL) reportCalls.add(b.id)
        if (b.type === "tool_result" && reportCalls.has(b.tool_use_id) && !b.is_error) {
          const id = reportIdOf(b.content)
          if (id) out.push(reportBubble(id))
        }
      }
    }
    if (m.role !== "user" && m.role !== "assistant") continue
    const text = textOf(m.content)
    if (!text) continue
    out.push({ id: m.id, role: m.role, text })
  }
  return out
}

function busyFor(tool: string): HelpBusy {
  if (tool === "help_search") return "search"
  if (tool === "help_read") return "read"
  return "think"
}

/** Wendet ein Stream-Ereignis auf den Verlauf an (neue Liste, die alte bleibt unverändert). */
export function applyHelpEvent(bubbles: HelpBubble[], ev: RunnerEvent): HelpBubble[] {
  const list = [...bubbles]
  const last = list.at(-1)
  const live = last && last.id === LIVE && last.role === "assistant" ? last : null
  const setLive = (patch: Partial<HelpBubble>) => {
    const next: HelpBubble = { id: LIVE, role: "assistant", text: live?.text ?? "", busy: live?.busy, ...patch }
    if (live) list[list.length - 1] = next
    else list.push(next)
  }

  switch (ev.type) {
    case "text_delta":
      setLive({ text: (live?.text ?? "") + ev.text, busy: undefined })
      break
    case "text":
      if (!live?.text) setLive({ text: ev.text, busy: undefined })
      break
    case "tool_use_start":
      setLive({ text: "", busy: busyFor(ev.tool_name) })   // Vorrede vor dem Werkzeug verwerfen
      break
    case "tool_use_result": {
      const id = ev.tool_name === REPORT_TOOL && ev.success ? reportIdOf(ev.output) : null
      if (id) {
        if (live) list.pop()                 // Karte vor die folgende Antwort, die Live-Blase danach neu
        list.push(reportBubble(id))
      }
      break
    }
    case "error":
      if (live) list.pop()
      list.push({ id: LIVE, role: "error", text: ev.message })
      break
    case "done":
      if (live) list[list.length - 1] = { id: ev.message_id || LIVE, role: "assistant", text: live.text }
      break
    default:
      break
  }
  return list
}
