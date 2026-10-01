/* Verteilt Live-Sync-Pings einer Session ({"t":"start"|"activity"|"done"})
   an weitere Teile der Oberfläche, ohne eine zweite SSE-Verbindung zu öffnen.
   useChat hält das eine Abo und reicht jeden Ping hier weiter. */

type Listener = (kind: string) => void

const listeners = new Map<string, Set<Listener>>()

export function emitSessionPing(sessionId: string, kind: string): void {
  listeners.get(sessionId)?.forEach((l) => l(kind))
}

/** Liefert eine Abmelde-Funktion. */
export function onSessionPing(sessionId: string, listener: Listener): () => void {
  let set = listeners.get(sessionId)
  if (!set) { set = new Set(); listeners.set(sessionId, set) }
  set.add(listener)
  return () => {
    set.delete(listener)
    if (set.size === 0) listeners.delete(sessionId)
  }
}
