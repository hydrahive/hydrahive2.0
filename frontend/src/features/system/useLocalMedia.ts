import { useEffect, useState } from "react"
import { actionOutcome, localMediaApi, type LocalMediaStatus } from "./localMediaApi"

export type LocalMediaAction = "install" | "uninstall"
export type LocalMediaPhase = "idle" | "confirm" | "running" | "done" | "failed"

const POLL_MS = 2000
// Der Download von ~33 GB kann lange dauern, das Log bleibt sichtbar.
const MAX_WAIT_MS = 3 * 60 * 60 * 1000

export function useLocalMedia() {
  const [status, setStatus] = useState<LocalMediaStatus | null>(null)
  const [action, setAction] = useState<LocalMediaAction>("install")
  const [phase, setPhase] = useState<LocalMediaPhase>("idle")
  const [log, setLog] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    try {
      const next = await localMediaApi.status()
      setStatus(next)
      return next
    } catch {
      return null
    }
  }

  useEffect(() => {
    const first = setTimeout(() => {
      void reload().then((next) => {
        // Nach einem Neuladen der Seite eine laufende Aktion wieder anzeigen.
        if (next?.running) {
          setAction(next.installed ? "uninstall" : "install")
          setPhase("running")
        }
      })
    }, 0)
    return () => clearTimeout(first)
  }, [])

  useEffect(() => {
    if (phase !== "running") return
    let alive = true
    const startedAt = Date.now()
    async function poll() {
      try {
        const r = await localMediaApi.log(300)
        if (!alive) return
        if (r.exists) setLog(r.lines)
        const next = await reload()
        if (!alive || next?.running) return
        const outcome = actionOutcome(r.lines)
        if (outcome === "ok") setPhase("done")
        else if (outcome === "failed") setPhase("failed")
      } catch { /* Server kann kurz weg sein, weiter pollen */ }
      if (alive && Date.now() - startedAt > MAX_WAIT_MS) setPhase("failed")
    }
    void poll()
    const timer = setInterval(poll, POLL_MS)
    return () => { alive = false; clearInterval(timer) }
  }, [phase])

  function ask(next: LocalMediaAction) {
    setAction(next); setError(null); setPhase("confirm")
  }

  async function confirm() {
    setError(null); setLog([])
    try {
      await (action === "install" ? localMediaApi.install() : localMediaApi.uninstall())
      setPhase("running")
    } catch (e) {
      setPhase("failed")
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  function close() {
    setPhase("idle"); setLog([]); setError(null)
  }

  return { status, action, phase, log, error, ask, confirm, close }
}
