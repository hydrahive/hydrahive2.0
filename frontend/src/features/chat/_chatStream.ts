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
// Blocks und schreiben höchstens einmal pro Animation-Frame in den State.
let pendingBlocks: ContentBlock[] | null = null
let rafHandle: number | null = null

const supportsRaf = typeof requestAnimationFrame === "function"

function flushLive(setState: SetState) {
  rafHandle = null
  const blocks = pendingBlocks
  pendingBlocks = null
  if (!blocks) return
  setState((s) => {
    const msgs = [...s.messages]
    const last = msgs[msgs.length - 1]
    if (last && last.id.startsWith("live-")) {
      msgs[msgs.length - 1] = { ...last, content: blocks }
    }
    return { ...s, messages: msgs }
  })
}

export function updateLive(setState: SetState, blocks: ContentBlock[]) {
  const snapshot = [...blocks]
  if (!supportsRaf) {
    pendingBlocks = snapshot
    flushLive(setState)
    return
  }
  pendingBlocks = snapshot
  if (rafHandle === null) {
    rafHandle = requestAnimationFrame(() => flushLive(setState))
  }
}

/** Erzwingt das sofortige Anwenden eines gepufferten Live-Updates. Muss vor
 *  jedem Reload/Abschluss laufen, damit kein Frame verloren geht. */
export function flushPendingLive(setState: SetState) {
  if (rafHandle !== null && supportsRaf) {
    cancelAnimationFrame(rafHandle)
    rafHandle = null
  }
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
