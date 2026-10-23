// Hilfe-Assistent (docs/plans/help-assistant.md): Knopf unten rechts auf jeder Seite.
// Im LayoutHost eingehängt (shared/Layout.tsx) → bleibt beim Seitenwechsel offen, Verlauf bleibt im State.
import { useCallback, useEffect, useRef, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { applyHelpEvent, messagesToBubbles, type HelpBubble } from "./_helpThread"
import { HelpAssistantView, type HelpStatus } from "./HelpAssistantView"
import { helpApi, readOpen, sendHelpMessage, writeOpen } from "./helpApi"

export function HelpAssistant() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const [open, setOpen] = useState(readOpen)
  const [status, setStatus] = useState<HelpStatus>("loading")
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [bubbles, setBubbles] = useState<HelpBubble[]>([])
  const [draft, setDraft] = useState("")
  const [sending, setSending] = useState(false)
  const loaded = useRef(false)

  // Zustand erst beim ersten Öffnen holen – sonst legte jeder Seitenaufruf einen Hilfe-Agenten an.
  const load = useCallback(async () => {
    setStatus("loading")
    try {
      const st = await helpApi.state()
      if (st.model_missing || !st.session_id) { setStatus("model_missing"); return }
      setSessionId(st.session_id)
      setBubbles(messagesToBubbles(await helpApi.messages(st.session_id)))
      setStatus("ready")
      loaded.current = true
    } catch {
      setStatus("error")
    }
  }, [])

  useEffect(() => {
    if (open && !loaded.current) void load()
  }, [open, load])

  const toggle = () => setOpen((o) => { writeOpen(!o); return !o })

  const send = async () => {
    const text = draft.trim()
    if (!text || !sessionId || sending) return
    setDraft("")
    setSending(true)
    setBubbles((b) => [...b, { id: `u-${Date.now()}`, role: "user", text }])
    try {
      for await (const ev of sendHelpMessage(sessionId, text, pathname)) {
        setBubbles((b) => applyHelpEvent(b, ev))
      }
    } catch (e) {
      const code = (e as { code?: string }).code
      if (code === "helpdesk_model_missing") { setStatus("model_missing"); loaded.current = false }
      else setBubbles((b) => applyHelpEvent(b, { type: "error", message: e instanceof Error ? e.message : String(e),
        fatal: true }))
    } finally {
      setSending(false)
    }
  }

  const openLlm = () => { loaded.current = false; navigate("/llm") }

  // Nach dem Einrichten der KI erneut versuchen, sobald das Fenster offen ist und die Seite wechselt.
  useEffect(() => {
    if (open && status === "model_missing" && !loaded.current && pathname !== "/llm") void load()
  }, [pathname]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <HelpAssistantView open={open} status={status} bubbles={bubbles} sending={sending} draft={draft}
      onToggle={toggle} onDraft={setDraft} onSend={() => void send()} onOpenLlm={openLlm} />
  )
}
