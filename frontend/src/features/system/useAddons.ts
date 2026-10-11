import { useEffect, useState } from "react"
import { addonOutcome, addonsApi, lastRun, type AddonId, type AddonItem } from "./addonsApi"

export type AddonPhase = "idle" | "confirm" | "running" | "done" | "failed"

const POLL_MS = 2000
// Voice lädt Modelle, VMs/Container ziehen Pakete – großzügig warten, das Log bleibt sichtbar.
const MAX_WAIT_MS = 90 * 60 * 1000

/** Zusatz-Module: Liste laden, Installation anfragen, Log mitlesen (auch über einen Dienst-Neustart hinweg). */
export function useAddons() {
  const [items, setItems] = useState<AddonItem[] | null>(null)
  const [running, setRunning] = useState<string | null>(null)
  const [target, setTarget] = useState<AddonId | null>(null)
  const [phase, setPhase] = useState<AddonPhase>("idle")
  const [log, setLog] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    try {
      const next = await addonsApi.list()
      setItems(next.items); setRunning(next.running)
      return next
    } catch {
      return null      // Dienst startet evtl. gerade neu (VMs/Container) – nächster Versuch holt es nach
    }
  }

  useEffect(() => {
    const first = setTimeout(() => {
      void reload().then((next) => {
        // Nach einem Neuladen der Seite einen laufenden Auftrag wieder anzeigen.
        const id = next?.items.find((i) => i.id === next.running)?.id
        if (id) { setTarget(id); setPhase("running") }
      })
    }, 0)
    return () => clearTimeout(first)
  }, [])

  useEffect(() => {
    if (phase !== "running" || !target) return
    let alive = true
    const startedAt = Date.now()
    async function poll() {
      try {
        const r = await addonsApi.log(300)
        if (!alive) return
        const lines = lastRun(r.exists ? r.lines : [])
        setLog(lines)
        const next = await reload()
        if (!alive || !next || next.running) return
        const outcome = addonOutcome(lines, target!)
        if (outcome === "ok") setPhase("done")
        else if (outcome === "failed") setPhase("failed")
      } catch { /* Server kann kurz weg sein (Neustart), weiter pollen */ }
      if (alive && Date.now() - startedAt > MAX_WAIT_MS) setPhase("failed")
    }
    void poll()
    const timer = setInterval(poll, POLL_MS)
    return () => { alive = false; clearInterval(timer) }
  }, [phase, target])

  function ask(id: AddonId) {
    setTarget(id); setError(null); setPhase("confirm")
  }

  async function confirm() {
    if (!target) return
    setError(null); setLog([])
    try {
      await addonsApi.install(target)
      setRunning(target); setPhase("running")
    } catch (e) {
      setPhase("failed"); setError(e instanceof Error ? e.message : String(e))
    }
  }

  function close() {
    setPhase("idle"); setTarget(null); setLog([]); setError(null)
  }

  return { items, running, target, phase, log, error, ask, confirm, close }
}
