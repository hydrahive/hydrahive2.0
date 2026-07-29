import { useCallback, useEffect, useRef, useState } from "react"
import { attachRun, chatApi, sendMessage, subscribeSession } from "./api"
import { applyStreamEvent, flushPendingLive } from "./_chatStream"
import type { ContentBlock, Message } from "./types"

export interface PendingConfirm {
  call_id: string
  tool_name: string
  arguments: Record<string, unknown>
  // Gesetzt vom Harakiri-Schutz: warum dieser shell_exec bestätigt werden muss.
  reason?: string | null
}

export interface ChatState {
  messages: Message[]
  busy: boolean
  compacting: boolean
  iteration: number
  error: string | null
  errorKind: string | null
  pendingConfirm: PendingConfirm | null
  lastTurnTokens: {
    input: number
    output: number
    cache_creation: number
    cache_read: number
  } | null
}

const EMPTY_STATE: ChatState = {
  messages: [], busy: false, compacting: false, iteration: 0,
  error: null, errorKind: null, pendingConfirm: null, lastTurnTokens: null,
}

export function useChat(sessionId: string | null) {
  const [state, setState] = useState<ChatState>(EMPTY_STATE)
  const abortRef = useRef<AbortController | null>(null)

  // True solange ein Run für diese Session aktiv beobachtet wird (Sende- oder
  // Reconnect-Stream). reload() darf busy dann NICHT auf false zwingen, sonst
  // verschwindet der Stop-Button nach F5 mitten im Lauf.
  const runningRef = useRef(false)

  // Stop: cancelt den Server-Task (funktioniert IMMER, auch nach Reconnect),
  // danach das lokale Zuhören beenden. Kein Verlass mehr auf Verbindungsabbruch.
  const cancel = useCallback(() => {
    runningRef.current = false
    if (sessionId) { void chatApi.stopRun(sessionId).catch(() => {}) }
    abortRef.current?.abort(); abortRef.current = null
    setState((s) => ({ ...s, busy: false }))
  }, [sessionId])

  const reload = useCallback(async () => {
    if (!sessionId) { setState(EMPTY_STATE); return }
    try {
      const msgs = await chatApi.listMessages(sessionId)
      // busy bleibt true, wenn gerade ein Run läuft (Reconnect/Sende-Stream) —
      // die Wahrheit ist der Server-Run-Status, nicht der lokale Ladevorgang.
      const stillRunning = runningRef.current
      // max_iterations-Error bleibt stehen bis der User "weitermachen" klickt —
      // Live-Sync-Reload darf ihn nicht wegwischen.
      setState((s) => ({
        ...s, messages: msgs, busy: stillRunning, iteration: stillRunning ? s.iteration : 0,
        error: s.errorKind === "max_iterations" ? s.error : null,
        errorKind: s.errorKind === "max_iterations" ? s.errorKind : null,
      }))
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
        return { ...s, messages: [...trimmed, userMsg, liveAssistant], busy: true, compacting: false, iteration: 1, error: null, errorKind: null, lastTurnTokens: null }
      })

      const blocks: ContentBlock[] = []
      const controller = new AbortController()
      abortRef.current = controller
      runningRef.current = true
      try {
        for await (const ev of sendMessage(sessionId, text, files, controller.signal, resendMessageId)) {
          const result = applyStreamEvent(ev as Record<string, unknown>, blocks, setState)
          if (result === "error") { runningRef.current = false; return }
          if (result === "done") { runningRef.current = false; await reload(); return }
        }
      } catch (e) {
        flushPendingLive(setState)
        const aborted = (e as DOMException)?.name === "AbortError"
        setState((s) => ({
          ...s,
          error: aborted ? null : (e instanceof Error ? e.message : "Stream-Fehler"),
          busy: false,
        }))
        if (aborted) await reload()
      } finally { runningRef.current = false; abortRef.current = null }
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

  // Live-Sync v1: passives Gerät/Tab lädt nach, wenn ein Lauf die Session bewegt
  // (egal welches Gerät ihn ausgelöst hat). Refs halten busy/reload für die
  // langlebige Subscription-Closure frisch.
  const busyRef = useRef(state.busy)
  busyRef.current = state.busy
  const reloadRef = useRef(reload)
  reloadRef.current = reload

  useEffect(() => {
    if (!sessionId) return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | null = null
    const onPing = () => {
      // Eigener Sende-Stream rendert schon (busy) → kein Reload-Clobber.
      // Schon ein Reload eingeplant (timer) → debouncen.
      if (busyRef.current || timer) return
      timer = setTimeout(() => { timer = null; void reloadRef.current() }, 400)
    }
    void subscribeSession(sessionId, onPing, controller.signal)
    return () => { controller.abort(); if (timer) clearTimeout(timer) }
  }, [sessionId])

  // Reconnect-in-Lauf: Beim Öffnen einer Session prüfen, ob dort schon ein Run
  // läuft (von diesem oder einem anderen Gerät). Wenn ja: an den Event-Bus
  // anhängen → live weiterschauen (flüssig) + Stop-Button aktiv. Der eigene
  // Sende-Stream (busy schon true) übernimmt selbst, daher hier nur wenn NICHT busy.
  useEffect(() => {
    if (!sessionId) return
    const controller = new AbortController()
    let cancelled = false
    ;(async () => {
      try {
        const st = await chatApi.runStatus(sessionId)
        if (cancelled || !st.running || busyRef.current) return
        runningRef.current = true
        setState((s) => ({ ...s, busy: true }))
        abortRef.current = controller
        const blocks: ContentBlock[] = []
        for await (const ev of attachRun(sessionId, st.latest_seq, controller.signal)) {
          const result = applyStreamEvent(ev as Record<string, unknown>, blocks, setState)
          if (result === "error") break
          if (result === "done") break
        }
      } catch {
        /* Run schon vorbei / Abbruch — reload holt den Endstand */
      } finally {
        runningRef.current = false
        if (abortRef.current === controller) abortRef.current = null
        if (!cancelled) { await reload() }
      }
    })()
    return () => { cancelled = true; controller.abort() }
  }, [sessionId, reload])

  return { ...state, send, cancel, reload, confirmTool }
}
