/**
 * Stream-Event-Processing für useChat: jedes SSE-Event wird hier gemappt auf ChatState-Änderungen.
 */
import type React from "react"
import type { ContentBlock } from "./types"
import type { ChatState } from "./useChat"

type SetState = React.Dispatch<React.SetStateAction<ChatState>>

// Coalescing der Live-Updates: schnelles Token-Streaming feuert sonst hunderte
// setState-Aufrufe pro Sekunde, jeder rendert den kompletten Thread neu und
// blockiert den Main-Thread (Tastatureingabe ruckelt). Wir puffern die letzten
// Blocks und schreiben zeitgetaktet in den State.
let pendingBlocks: ContentBlock[] | null = null
let rafHandle: number | null = null
let lastFlush = 0

const supportsRaf = typeof requestAnimationFrame === "function"

// Ein Frame (16 ms) reicht in langen Threads nicht: React rendert den Baum nicht
// schnell genug, die Updates stauen sich und die Antwort baut sich sichtbar
// zeilenweise auf. Ein ruhigeres Intervall wirkt flüssiger und hält den
// Main-Thread frei — sichtbar wird derselbe Text, nur ohne Ruckeln.
const MIN_FLUSH_MS = 70

function now(): number {
  return typeof performance === "object" && typeof performance.now === "function"
    ? performance.now()
    : Date.now()
}

function flushLive(setState: SetState) {
  rafHandle = null
  const blocks = pendingBlocks
  pendingBlocks = null
  if (!blocks) return
  lastFlush = now()
  setState((s) => {
    const msgs = s.messages
    const lastIndex = msgs.length - 1
    const last = msgs[lastIndex]
    if (!last || !last.id.startsWith("live-")) return s
    // Nur das letzte Element ersetzen; die übrigen Referenzen bleiben identisch,
    // damit memoisierte Nachrichten-Komponenten nicht neu rendern.
    const next = msgs.slice()
    next[lastIndex] = { ...last, content: blocks }
    return { ...s, messages: next }
  })
}

export function updateLive(setState: SetState, blocks: ContentBlock[]) {
  pendingBlocks = [...blocks]
  if (!supportsRaf) {
    flushLive(setState)
    return
  }
  if (rafHandle !== null) return
  const wait = Math.max(0, MIN_FLUSH_MS - (now() - lastFlush))
  if (wait === 0) {
    rafHandle = requestAnimationFrame(() => flushLive(setState))
    return
  }
  rafHandle = window.setTimeout(() => {
    rafHandle = null
    flushLive(setState)
  }, wait) as unknown as number
}

/** Erzwingt das sofortige Anwenden eines gepufferten Live-Updates. Muss vor
 *  jedem Reload/Abschluss laufen, damit kein Frame verloren geht. */
export function flushPendingLive(setState: SetState) {
  if (rafHandle !== null && supportsRaf) {
    // Der Handle stammt je nach Pfad von rAF oder setTimeout — beide abräumen.
    cancelAnimationFrame(rafHandle)
    clearTimeout(rafHandle)
    rafHandle = null
  }
  lastFlush = 0
  if (pendingBlocks) flushLive(setState)
}

export function applyStreamEvent(
  ev: Record<string, unknown>,
  blocks: ContentBlock[],
  setState: SetState,
): "continue" | "done" | "error" {
  if (ev.type === "compaction_start") {
    setState((s) => ({ ...s, compacting: true }))
  } else if (ev.type === "iteration_start") {
    setState((s) => ({ ...s, iteration: ev.iteration as number }))
  } else if (ev.type === "message_start") {
    setState((s) => ({ ...s, compacting: false }))
    blocks.push({ type: "text", text: "" })
    updateLive(setState, blocks)
  } else if (ev.type === "text_delta") {
    const last = blocks[blocks.length - 1]
    if (last && last.type === "text") {
      last.text += ev.text as string
    } else {
      blocks.push({ type: "text", text: ev.text as string })
    }
    updateLive(setState, blocks)
  } else if (ev.type === "text") {
    blocks.push({ type: "text", text: ev.text as string })
    updateLive(setState, blocks)
  } else if (ev.type === "tool_use_start") {
    blocks.push({
      type: "tool_use",
      id: ev.call_id as string,
      name: ev.tool_name as string,
      input: ev.arguments as Record<string, unknown>,
    })
    flushPendingLive(setState)
    updateLive(setState, blocks)
  } else if (ev.type === "tool_confirm_required") {
    setState((s) => ({
      ...s,
      pendingConfirm: {
        call_id: ev.call_id as string,
        tool_name: ev.tool_name as string,
        arguments: ev.arguments as Record<string, unknown>,
        reason: (ev.reason as string | null | undefined) ?? null,
      },
    }))
  } else if (ev.type === "tool_use_result") {
    setState((s) => s.pendingConfirm?.call_id === ev.call_id ? { ...s, pendingConfirm: null } : s)
    blocks.push({
      type: "tool_result",
      tool_use_id: ev.call_id as string,
      content: typeof ev.output === "string" ? ev.output : JSON.stringify(ev.output, null, 2),
      is_error: !ev.success as boolean,
    })
    flushPendingLive(setState)
    updateLive(setState, blocks)
  } else if (ev.type === "error") {
    flushPendingLive(setState)
    const meta = ev.metadata as { kind?: string } | undefined
    setState((s) => ({
      ...s,
      error: ev.message as string,
      errorKind: meta?.kind ?? null,
      busy: false,
    }))
    return "error"
  } else if (ev.type === "done") {
    flushPendingLive(setState)
    setState((s) => ({
      ...s, busy: false,
      lastTurnTokens: {
        input: ev.input_tokens as number,
        output: ev.output_tokens as number,
        cache_creation: ev.cache_creation_tokens as number,
        cache_read: ev.cache_read_tokens as number,
      },
    }))
    return "done"
  }
  return "continue"
}
