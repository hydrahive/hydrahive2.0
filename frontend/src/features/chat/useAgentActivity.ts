import { useEffect, useRef, useState } from "react"
import { subscribeAgentActivity, type ActivityEntry } from "./api"

const DONE_LINGER_MS = 2500

/**
 * Hält den Live-Stand laufender Agenten (SSE) + einen kurzen „done"-Nachklang,
 * damit Männchen nicht abrupt verschwinden. Nur aktiv wenn `enabled`.
 */
export function useAgentActivity(enabled: boolean): { running: ActivityEntry[]; doneNames: string[] } {
  const [running, setRunning] = useState<ActivityEntry[]>([])
  const [doneNames, setDoneNames] = useState<string[]>([])
  const prevNames = useRef<Set<string>>(new Set())
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])

  useEffect(() => {
    if (!enabled) return
    const controller = new AbortController()
    void subscribeAgentActivity((agents) => {
      const names = new Set(agents.map((a) => a.name))
      const justDone = [...prevNames.current].filter((n) => !names.has(n))
      prevNames.current = names
      setRunning(agents)
      if (justDone.length) {
        setDoneNames((d) => [...new Set([...d, ...justDone])])
        justDone.forEach((n) =>
          timers.current.push(setTimeout(
            () => setDoneNames((d) => d.filter((x) => x !== n)), DONE_LINGER_MS)))
      }
    }, controller.signal)
    return () => {
      controller.abort()
      prevNames.current = new Set()
      timers.current.forEach(clearTimeout)
      timers.current = []
    }
  }, [enabled])

  if (!enabled) return { running: [], doneNames: [] }
  const liveNames = new Set(running.map((a) => a.name))
  return { running, doneNames: doneNames.filter((n) => !liveNames.has(n)) }
}
