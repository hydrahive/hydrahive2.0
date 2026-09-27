import { useEffect, useRef } from "react"

/**
 * App-weites Signal "ein Agent-Lauf ist beendet" (done oder error).
 * Ansichten, die Agent-Ergebnisse zeigen (z. B. Dateibäume), laden daraufhin
 * neu — ohne Polling und ohne Kopplung an einen bestimmten Chat.
 */
const EVENT = "hh-run-finished"

export function notifyRunFinished(): void {
  window.dispatchEvent(new Event(EVENT))
}

/** Ruft `onFinished` nach jedem beendeten Agent-Lauf auf. */
export function useRunFinished(onFinished: () => void): void {
  const ref = useRef(onFinished)
  useEffect(() => { ref.current = onFinished }, [onFinished])
  useEffect(() => {
    const handler = () => ref.current()
    window.addEventListener(EVENT, handler)
    return () => window.removeEventListener(EVENT, handler)
  }, [])
}
