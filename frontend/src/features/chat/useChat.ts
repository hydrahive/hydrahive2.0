import { useCallback, useRef, useState } from "react"
import { chatApi, sendMessage } from "./api"
import type { ContentBlock, Message } from "./types"

export interface ChatState {
  messages: Message[]
  busy: boolean
  iteration: number
  error: string | null
  lastTurnTokens: {
    input: number
    output: number
    cache_creation: number
    cache_read: number
  } | null
}

export function useChat(sessionId: string | null) {
  const [state, setState] = useState<ChatState>({
    messages: [],
    busy: false,
    iteration: 0,
    error: null,
    lastTurnTokens: null,
  })
  const abortRef = useRef<AbortController | null>(null)

  const cancel = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
  }, [])

  const reload = useCallback(async () => {
    if (!sessionId) {
      setState({ messages: [], busy: false, iteration: 0, error: null })
      return
    }
    try {
      const msgs = await chatApi.listMessages(sessionId)
      setState({ messages: msgs, busy: false, iteration: 0, error: null })
    } catch (e) {
      setState((s) => ({ ...s, error: e instanceof Error ? e.message : "Fehler" }))
    }
  }, [sessionId])

  const send = useCallback(
    async (text: string) => {
      if (!sessionId) return
      const userMsg: Message = {
        id: `local-${Date.now()}`,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
        token_count: null,
        metadata: {},
      }
      const liveAssistant: Message = {
        id: `live-${Date.now()}`,
        role: "assistant",
        content: [],
        created_at: new Date().toISOString(),
        token_count: null,
        metadata: {},
      }
      setState((s) => ({
        ...s,
        messages: [...s.messages, userMsg, liveAssistant],
        busy: true,
        iteration: 1,
        error: null,
      }))

      const blocks: ContentBlock[] = []
      const controller = new AbortController()
      abortRef.current = controller
      try {
        for await (const ev of sendMessage(sessionId, text, controller.signal)) {
          if (ev.type === "iteration_start") {
            setState((s) => ({ ...s, iteration: ev.iteration }))
          } else if (ev.type === "message_start") {
            // neue Assistant-Bubble vorbereiten — leerer Text-Block
            blocks.push({ type: "text", text: "" })
            updateLive(setState, blocks)
          } else if (ev.type === "text_delta") {
            // an letzten Text-Block anhängen, oder neuen anlegen
            const last = blocks[blocks.length - 1]
            if (last && last.type === "text") {
              last.text += ev.text
            } else {
              blocks.push({ type: "text", text: ev.text })
            }
            updateLive(setState, blocks)
          } else if (ev.type === "text") {
            blocks.push({ type: "text", text: ev.text })
            updateLive(setState, blocks)
          } else if (ev.type === "tool_use_start") {
            blocks.push({
              type: "tool_use",
              id: ev.call_id,
              name: ev.tool_name,
              input: ev.arguments,
            })
            updateLive(setState, blocks)
          } else if (ev.type === "tool_use_result") {
            blocks.push({
              type: "tool_result",
              tool_use_id: ev.call_id,
              content: typeof ev.output === "string" ? ev.output : JSON.stringify(ev.output, null, 2),
              is_error: !ev.success,
            })
            updateLive(setState, blocks)
          } else if (ev.type === "error") {
            setState((s) => ({ ...s, error: ev.message, busy: false }))
            return
          } else if (ev.type === "done") {
            setState((s) => ({
              ...s,
              busy: false,
              lastTurnTokens: {
                input: ev.input_tokens,
                output: ev.output_tokens,
                cache_creation: ev.cache_creation_tokens,
                cache_read: ev.cache_read_tokens,
              },
            }))
            // Re-load from server to get canonical state with proper IDs
            await reload()
            return
          }
        }
      } catch (e) {
        const aborted = (e as DOMException)?.name === "AbortError"
        setState((s) => ({
          ...s,
          error: aborted ? null : (e instanceof Error ? e.message : "Stream-Fehler"),
          busy: false,
        }))
        if (aborted) await reload()
      } finally {
        abortRef.current = null
      }
    },
    [sessionId, reload],
  )

  return { ...state, send, cancel, reload }
}

function updateLive(
  setState: React.Dispatch<React.SetStateAction<ChatState>>,
  blocks: ContentBlock[],
) {
  setState((s) => {
    const msgs = [...s.messages]
    const last = msgs[msgs.length - 1]
    if (last && last.id.startsWith("live-")) {
      msgs[msgs.length - 1] = { ...last, content: [...blocks] }
    }
    return { ...s, messages: msgs }
  })
}
