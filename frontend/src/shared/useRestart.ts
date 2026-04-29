import { useState } from "react"
import { api } from "@/shared/api-client"
import type { RestartState } from "./RestartModal"

export function useRestart() {
  const [state, setState] = useState<"idle" | RestartState>("idle")
  const [error, setError] = useState<string | null>(null)

  function open() {
    setState("confirm")
    setError(null)
  }

  function close() {
    setState("idle")
  }

  async function confirm() {
    setState("starting")
    setError(null)
    try {
      await api.post<{ started: boolean }>("/system/restart", {})
    } catch (e) {
      setState("failed")
      setError(e instanceof Error ? e.message : String(e))
      return
    }
    setState("running")
    const startedAt = Date.now()
    const maxWaitMs = 60_000
    let backendDown = false
    while (Date.now() - startedAt < maxWaitMs) {
      await new Promise((r) => setTimeout(r, 1500))
      try {
        await fetch("/api/health", { signal: AbortSignal.timeout(3000) })
        if (backendDown) {
          setState("done")
          return
        }
      } catch {
        backendDown = true
      }
    }
    setState("failed")
    setError("timeout")
  }

  return { state, error, open, close, confirm }
}
