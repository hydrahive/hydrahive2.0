// Gemeinsamer Ablauf für „Alle updaten“ (Admin-Cockpit und Modul-Seite) – docs/specs/modul-update-alle.md.
import { useCallback, useEffect, useRef, useState } from "react"
import { updateAllModules } from "./api"
import { parseUpdateAll, type UpdateAllProgress } from "./updateAllProgress"

export interface UpdateAllState {
  running: boolean
  progress: UpdateAllProgress | null
  error: string | null
}

export function useUpdateAll(expectedTotal: number, onFinished: () => void) {
  const [state, setState] = useState<UpdateAllState>({ running: false, progress: null, error: null })
  const stopRef = useRef<(() => void) | null>(null)
  useEffect(() => () => stopRef.current?.(), [])

  const start = useCallback(() => {
    if (state.running || expectedTotal === 0) return
    const lines: string[] = []
    setState({ running: true, progress: parseUpdateAll([], expectedTotal), error: null })
    stopRef.current = updateAllModules(
      (line) => { lines.push(line); setState((s) => ({ ...s, progress: parseUpdateAll(lines, expectedTotal) })) },
      () => { stopRef.current = null; setState((s) => ({ ...s, running: false })); onFinished() },
      (msg) => {
        stopRef.current = null
        setState({ running: false, progress: parseUpdateAll(lines, expectedTotal), error: msg })
        onFinished()
      },
    )
  }, [state.running, expectedTotal, onFinished])

  const dismiss = useCallback(() => setState({ running: false, progress: null, error: null }), [])
  return { ...state, start, dismiss }
}
