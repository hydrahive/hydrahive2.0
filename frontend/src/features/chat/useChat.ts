import { useCallback, useRef, useState } from "react"
import { chatApi, sendMessage } from "./api"
import { applyStreamEvent, updateLive } from "./_chatStream"
import type { ContentBlock, Message } from "./types"

export interface PendingConfirm {
  call_id: string
  tool_name: string
  arguments: Record<string, unknown>
}

export interface ChatState {
  messages: Message[]
  busy: boolean
  iteration: number
  error: string | null
  pendingConfirm: PendingConfirm | null
  lastTurnTokens: {
    input: number
    output: number
    cache_creation: number
    cache_read: number
  } | null
}

const EMPTY_STATE: ChatState = {
  messages: [], busy: false, iteration: 0, error: null, pendingConfirm: null, lastTurnTokens: null,
}

export function useChat(sessionId: string | null) {
  const [state, setState] = useState<ChatState>(EMPTY_STATE)
  const abortRef = useRef<AbortController | null>(null)

  const cancel = useCallback(() => {
    abortRef.current?.abort(); abortRef.current = null
  }, [])

  const reload = useCallback(async () => {
    if (!sessionId) { setState(EMPTY_STATE); return }
    try {
      const msgs = await chatApi.listMessages(sessionId)
      setState((s) => ({ ...s, messages: msgs, busy: false, iteration: 0, error: null }))
    } catch (e) {
      setState((s) => ({ ...s, error: e instanceof Error ? e.message : "Fehler" }))
    }
  }, [sessionId])

  const send = useCallback(
    async (text: string, files: File[] = [], resendMessageId?: string) => {
      if (!sessionId) return
      const imageBlocks = files.filter((f) => f.type.startsWith("image/"))
        .map((f) => ({ type: "image" as const, source: { type: "url" as const, url: URL.createObjectURL(f) } }))
      const userMsg: Message = {
        id: `local-${Date.now()}`, role: "user",
        content: imageBlocks.length > 0 ? [...imageBlocks, { type: "text" as const, text }] : text,
        created_at: new Date().toISOString(), token_count: null, metadata: {},
      }
      const liveAssistant: Message = {
        id: `live-${Date.now()}`, role: "assistant", content: [],
        created_at: new Date().toISOString(), token_count: null, metadata: {},
      }
      setState((s) => {
        const trimmed = resendMessageId
          ? s.messages.slice(0, s.messages.findIndex((m) => m.id === resendMessageId))
          : s.messages
        return { ...s, messages: [...trimmed, userMsg, liveAssistant], busy: true, iteration: 1, error: null }
      })

      const blocks: ContentBlock[] = []
      const controller = new AbortController()
      abortRef.current = controller
      try {
        for await (const ev of sendMessage(sessionId, text, files, controller.signal, resendMessageId)) {
          const result = applyStreamEvent(ev as Record<string, unknown>, blocks, setState)
          if (result === "error") return
          if (result === "done") { await reload(); return }
        }
      } catch (e) {
        const aborted = (e as DOMException)?.name === "AbortError"
        setState((s) => ({
          ...s,
          error: aborted ? null : (e instanceof Error ? e.message : "Stream-Fehler"),
          busy: false,
        }))
        if (aborted) await reload()
      } finally { abortRef.current = null }
    },
    [sessionId, reload],
  )

  const confirmTool = useCallback(
    async (decision: "approve" | "deny") => {
      if (!sessionId || !state.pendingConfirm) return
      try {
        await chatApi.toolConfirm(sessionId, state.pendingConfirm.call_id, decision)
      } catch (e) {
        setState((s) => ({ ...s, error: e instanceof Error ? e.message : "Fehler" }))
      } finally {
        setState((s) => ({ ...s, pendingConfirm: null }))
      }
    },
    [sessionId, state.pendingConfirm],
  )

  return { ...state, send, cancel, reload, confirmTool }
}
