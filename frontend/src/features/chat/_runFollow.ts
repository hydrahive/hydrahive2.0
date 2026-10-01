/* An einen Lauf anhängen, den dieses Fenster NICHT selbst gestartet hat:
   - beim Öffnen einer Session, in der schon etwas läuft (Reconnect, F5),
   - beim Ping {"t":"start"}: anderes Gerät oder der Server selbst (Auswertung
     von Spezialisten-Ergebnissen, docs/specs/agent-background-delegation.md).
   Dann wird live gestreamt und der Stopp-Knopf ist aktiv. */
import type React from "react"
import { attachRun, chatApi } from "./api"
import { applyStreamEvent } from "./_chatStream"
import type { ContentBlock, Message } from "./types"
import type { ChatState } from "./useChat"

type SetState = React.Dispatch<React.SetStateAction<ChatState>>

export interface FollowDeps {
  sessionId: string
  controller: AbortController
  setState: SetState
  runningRef: React.MutableRefObject<boolean>
  busyRef: React.MutableRefObject<boolean>
  abortRef: React.MutableRefObject<AbortController | null>
  reload: () => Promise<void>
}

/** fromStart: beim Start-Ping den Event-Puffer ab 0 lesen (er gehört frisch
 *  zu diesem Lauf). Beim Reconnect ab jetzt; Älteres kommt über den Reload. */
export async function followRun(d: FollowDeps, fromStart: boolean): Promise<void> {
  let attached = false
  try {
    const st = await chatApi.runStatus(d.sessionId)
    // Eigener Sende-Stream oder schon angehängt → nichts tun (nach dem await
    // prüfen und sofort setzen: JS ist hier atomar, kein Doppel-Anhängen).
    if (d.controller.signal.aborted || !st.running || d.busyRef.current || d.runningRef.current) return
    attached = true
    d.runningRef.current = true
    d.abortRef.current = d.controller
    if (fromStart) {
      // Neuer Lauf: auslösende Nachricht (z. B. Spezialisten-Ergebnis) laden,
      // dann die Antwort live in einen Platzhalter streamen — wie beim Senden.
      d.setState((s) => ({ ...s, busy: true, error: null, errorKind: null }))
      await d.reload()
      if (d.controller.signal.aborted) return
      const live: Message = {
        id: `live-${Date.now()}`, role: "assistant", content: [],
        created_at: new Date().toISOString(), token_count: null, metadata: {},
      }
      d.setState((s) => ({ ...s, messages: [...s.messages, live] }))
    } else {
      // Reconnect mitten im Lauf: nur Stopp-Knopf + Endstand (wie bisher);
      // ein Platzhalter begänne mitten im Satz.
      d.setState((s) => ({ ...s, busy: true }))
    }
    const blocks: ContentBlock[] = []
    for await (const ev of attachRun(d.sessionId, fromStart ? 0 : st.latest_seq, d.controller.signal)) {
      if (applyStreamEvent(ev as Record<string, unknown>, blocks, d.setState) !== "continue") break
    }
  } catch {
    /* Lauf schon vorbei oder Abbruch — der Reload holt den Endstand */
  } finally {
    if (attached) {
      d.runningRef.current = false
      if (d.abortRef.current === d.controller) d.abortRef.current = null
      // Selbst freigeben — schlägt der Reload fehl, hinge sonst der Stopp-Knopf.
      d.setState((s) => ({ ...s, busy: false }))
      if (!d.controller.signal.aborted) await d.reload()
    }
  }
}

/** Typ eines Live-Sync-Frames („start“, „activity“, „done“) oder null. */
export function pingKind(frame: string): string | null {
  const line = frame.split("\n").find((l) => l.startsWith("data:"))
  if (!line) return null
  try {
    const t = (JSON.parse(line.slice(5).trim()) as { t?: unknown }).t
    return typeof t === "string" ? t : ""
  } catch {
    return ""
  }
}
