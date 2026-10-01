import { useCallback, useEffect, useRef, useState } from "react"
import { delegationsApi, type Delegation } from "./delegationsApi"
import { isRefreshPing, POLL_MS, shouldPoll } from "./_delegationPolling"
import { onSessionPing } from "./_sessionPings"

/** Hintergrund-Aufträge einer Session. Lädt sofort bei Session-Wechsel,
 *  Lauf-Start/-Ende (auch auf anderem Gerät) und fragt alle 5 s ab, solange
 *  etwas läuft, ein eigener Lauf aktiv ist oder dieser gerade geendet hat. */
export function useDelegations(sessionId: string | null, busy: boolean) {
  const [items, setItems] = useState<Delegation[]>([])
  const [undelivered, setUndelivered] = useState(false)
  const [now, setNow] = useState(() => Date.now())
  const [loadedFor, setLoadedFor] = useState<string | null>(null)
  const alive = useRef(true)
  const prevBusy = useRef(busy)
  const runEndedAt = useRef<number | null>(null)

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

  // Lauf startet/endet (eigener, anderes Gerät, Zustellung) → sofort neu laden.
  useEffect(() => {
    if (!sessionId) return
    return onSessionPing(sessionId, (kind) => { if (isRefreshPing(kind)) void refresh() })
  }, [sessionId, refresh])

  // Daten einer anderen (vorherigen) Session nie anzeigen.
  const current = loadedFor !== null && loadedFor === sessionId
  const running = current ? items.filter((d) => d.status === "running") : []
  const runningCount = running.length

  useEffect(() => {
    if (prevBusy.current && !busy) runEndedAt.current = Date.now()
    prevBusy.current = busy
    const state = () => ({
      hasSession: !!sessionId, running: runningCount, busy,
      runEndedAt: runEndedAt.current, now: Date.now(),
    })
    if (!shouldPoll(state())) return
    const timer = setInterval(() => {
      if (!shouldPoll(state())) { clearInterval(timer); return }
      void refresh()
    }, POLL_MS)
    return () => clearInterval(timer)
  }, [sessionId, runningCount, busy, refresh])

  return { running, waiting: current && undelivered, now, refresh }
}
