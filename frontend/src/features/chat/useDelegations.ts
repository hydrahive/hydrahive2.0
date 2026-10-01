import { useCallback, useEffect, useRef, useState } from "react"
import { delegationsApi, type Delegation } from "./delegationsApi"

const POLL_MS = 5000

/** Hintergrund-Aufträge einer Session. Fragt alle 5 s ab, solange etwas läuft
 *  oder ein Lauf aktiv ist; sonst nur beim Wechsel von busy (Lauf-Ende). */
export function useDelegations(sessionId: string | null, busy: boolean) {
  const [items, setItems] = useState<Delegation[]>([])
  const [undelivered, setUndelivered] = useState(false)
  const [now, setNow] = useState(() => Date.now())
  const alive = useRef(true)

  const [loadedFor, setLoadedFor] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!sessionId) return
    try {
      const r = await delegationsApi.list(sessionId)
      if (!alive.current) return
      setItems(r.delegations)
      setUndelivered(r.undelivered)
      setLoadedFor(sessionId)
      setNow(Date.now())
    } catch {
      /* Abfrage ist best-effort; die Leiste bleibt im letzten Zustand */
    }
  }, [sessionId])

  useEffect(() => {
    alive.current = true
    // Laden beim Session-Wechsel/Lauf-Ende: setState erst nach dem await (async).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh()
    return () => { alive.current = false }
  }, [refresh, busy])

  // Daten einer anderen (vorherigen) Session nie anzeigen.
  const current = loadedFor !== null && loadedFor === sessionId
  const running = current ? items.filter((d) => d.status === "running") : []

  useEffect(() => {
    if (!sessionId || (running.length === 0 && !busy)) return
    const timer = setInterval(() => { void refresh() }, POLL_MS)
    return () => clearInterval(timer)
  }, [sessionId, running.length, busy, refresh])

  return { running, waiting: current && undelivered, now, refresh }
}
