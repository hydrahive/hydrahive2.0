import { useEffect, useState } from "react"
import { api } from "@/shared/api-client"
import { getModuleUpdateCount } from "@/features/modules/api"
import type { UpdateState } from "@/shared/UpdateModal"

export function useLayoutUpdate(isAdmin: boolean) {
  const [version, setVersion] = useState<string | null>(null)
  const [commit, setCommit] = useState<string | null>(null)
  const [updateBehind, setUpdateBehind] = useState<number | null>(null)
  const [moduleUpdateCount, setModuleUpdateCount] = useState(0)
  const [updateState, setUpdateState] = useState<"idle" | UpdateState>("idle")
  const [updateError, setUpdateError] = useState<string | null>(null)
  const [newCommit, setNewCommit] = useState<string | null>(null)

  useEffect(() => {
    function loadHealth() {
      api.get<{ version: string; commit: string | null; update_behind: number | null }>("/health")
        .then((r) => { setVersion(r.version); setCommit(r.commit); setUpdateBehind(r.update_behind) })
        .catch(() => {})
    }
    loadHealth()
    const t = setInterval(loadHealth, 5 * 60 * 1000)
    return () => clearInterval(t)
  }, [])

  // Modul-Update-Zähler nur für Admins (Endpoint ist admin-gated). Billiger
  // Cache-Read im Backend (kein git-pull) — trotzdem selten pollen.
  useEffect(() => {
    // Nur Admins fragen den (admin-gated) Zähler ab. Nicht-Admins: bleibt 0
    // (Initialwert) — kein synchroner setState im Effect nötig.
    if (!isAdmin) return
    function loadModuleUpdates() {
      getModuleUpdateCount()
        .then((r) => setModuleUpdateCount(r.count))
        .catch(() => {})
    }
    loadModuleUpdates()
    const t = setInterval(loadModuleUpdates, 15 * 60 * 1000)
    return () => clearInterval(t)
  }, [isAdmin])

  async function confirmUpdate() {
    setUpdateState("starting"); setUpdateError(null)

    const wasBehind = updateBehind !== 0
    if (wasBehind) {
      try {
        const fresh = await api.get<{ commit: string | null; update_behind: number | null }>("/system/check-update")
        if (fresh.update_behind === 0) {
          setCommit(fresh.commit); setUpdateBehind(0)
          setNewCommit(fresh.commit); setUpdateState("done"); return
        }
      } catch { /* ignore — POST trotzdem versuchen */ }
    }

    try {
      await api.post<{ started: boolean }>("/system/update", {})
    } catch (e) {
      setUpdateState("failed"); setUpdateError(e instanceof Error ? e.message : ""); return
    }
    setUpdateState("running")
    const oldCommit = commit
    const startedAt = Date.now()
    // Update braucht typisch 3-8min (git pull, deps, frontend build, agentlink,
    // service restart). Wir warten auf commit-change, max 10min.
    // Kein "15s-stable = done"-Fallback — der hat #zzz verursacht: Modal sagte
    // nach 15s "fertig" obwohl Update gerade erst angefangen hatte. Pre-Check
    // oben fängt schon den no-op-Fall (lokal bereits == remote) ab.
    while (Date.now() - startedAt < 10 * 60 * 1000) {
      await new Promise((r) => setTimeout(r, 3000))
      try {
        const h = await api.get<{ commit: string | null; update_behind: number | null }>("/health")
        if (h.commit && h.commit !== oldCommit) {
          setCommit(h.commit); setUpdateBehind(h.update_behind)
          setNewCommit(h.commit); setUpdateState("done"); return
        }
      } catch { /* Service restartet gerade — weiter pollen */ }
    }
    setUpdateState("failed"); setUpdateError("timeout")
  }

  return {
    version, commit, updateBehind, moduleUpdateCount,
    updateState, updateError, newCommit,
    confirmUpdate,
    openUpdateModal: () => { setUpdateState("confirm"); setUpdateError(null); setNewCommit(null) },
    closeUpdateModal: () => setUpdateState("idle"),
  }
}
