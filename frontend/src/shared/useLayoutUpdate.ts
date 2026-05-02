import { useEffect, useState } from "react"
import { api } from "@/shared/api-client"
import type { UpdateState } from "@/shared/UpdateModal"

export function useLayoutUpdate() {
  const [version, setVersion] = useState<string | null>(null)
  const [commit, setCommit] = useState<string | null>(null)
  const [updateBehind, setUpdateBehind] = useState<number | null>(null)
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

  async function confirmUpdate() {
    setUpdateState("starting"); setUpdateError(null)
    try {
      await api.post<{ started: boolean }>("/system/update", {})
    } catch (e) {
      setUpdateState("failed"); setUpdateError(e instanceof Error ? e.message : ""); return
    }
    setUpdateState("running")
    const oldCommit = commit
    const startedAt = Date.now()
    while (Date.now() - startedAt < 5 * 60 * 1000) {
      await new Promise((r) => setTimeout(r, 3000))
      try {
        const h = await api.get<{ commit: string | null; update_behind: number | null }>("/health")
        if (h.commit && h.commit !== oldCommit) {
          setCommit(h.commit); setUpdateBehind(h.update_behind)
          setNewCommit(h.commit); setUpdateState("done"); return
        }
      } catch { /* server still restarting */ }
    }
    setUpdateState("failed"); setUpdateError("timeout")
  }

  return {
    version, commit, updateBehind,
    updateState, updateError, newCommit,
    confirmUpdate,
    openUpdateModal: () => { setUpdateState("confirm"); setUpdateError(null); setNewCommit(null) },
    closeUpdateModal: () => setUpdateState("idle"),
  }
}
