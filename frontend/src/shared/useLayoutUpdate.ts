import { useEffect, useRef, useState } from "react"
import { api } from "@/shared/api-client"
import { getModuleUpdateCount } from "@/features/modules/api"
import { pluginsApi } from "@/features/plugins/api"
import type { UpdateState } from "@/shared/UpdateModal"
import { isStale } from "@/shared/_staleBundle"
import { UPDATE_MAX_CHECKS, waitForUpdate } from "@/shared/_waitForUpdate"

export function useLayoutUpdate(isAdmin: boolean) {
  const [version, setVersion] = useState<string | null>(null)
  const [commit, setCommit] = useState<string | null>(null)
  const [updateBehind, setUpdateBehind] = useState<number | null>(null)
  const [moduleUpdateCount, setModuleUpdateCount] = useState(0)
  const [pluginUpdateCount, setPluginUpdateCount] = useState(0)
  const [updateState, setUpdateState] = useState<"idle" | UpdateState>("idle")
  const [updateError, setUpdateError] = useState<string | null>(null)
  const [newCommit, setNewCommit] = useState<string | null>(null)
  // Stand, mit dem DIESES Fenster geladen wurde (erste Health-Antwort).
  const loadedWith = useRef<string | null>(null)
  const [stale, setStale] = useState(false)

  useEffect(() => {
    function loadHealth() {
      api.get<{ version: string; commit: string | null; update_behind: number | null }>("/health")
        .then((r) => {
          setVersion(r.version); setCommit(r.commit); setUpdateBehind(r.update_behind)
          if (loadedWith.current === null) loadedWith.current = r.commit
          setStale(isStale(loadedWith.current, r.commit))
        })
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
      pluginsApi.updateCount()                       // Plugins wie Module (docs/specs/plugin-updates.md)
        .then((r) => setPluginUpdateCount(r.count))
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
    // Fertig bei neuem Commit ODER Schlusszeile „HH-UPDATE-ENDE“ im Log (auch ohne neuen Stand bzw. bei Abbruch,
    // Befund 22.10.2026). Kein „15s-stable = done“-Fallback – der meldete früher „fertig“ mitten im Update.
    // Höchstens 30 min (UPDATE_MAX_CHECKS × 3 s) – das Update hebt auch Systempakete an.
    const r = await waitForUpdate({
      logTotal: async () => (await api.get<{ total?: number }>("/system/update/log?tail=1")).total ?? 0,
      logSince: async (since) =>
        (await api.get<{ lines: string[] }>(`/system/update/log?tail=50&since=${since}`)).lines,
      health: async () => {
        const h = await api.get<{ commit: string | null; update_behind: number | null }>("/health")
        setUpdateBehind(h.update_behind)
        return h.commit
      },
      sleep: (ms) => new Promise((res) => setTimeout(res, ms)),
    }, commit, UPDATE_MAX_CHECKS)
    if (r.kind === "done") {
      const changed = !!r.commit && r.commit !== commit
      if (r.commit) setCommit(r.commit)
      setNewCommit(changed ? r.commit : null); setUpdateState("done"); return   // null → „keine neuen Änderungen“
    }
    setUpdateState("failed"); setUpdateError(r.reason)
  }

  return {
    version, commit, updateBehind, moduleUpdateCount, pluginUpdateCount, stale,
    updateState, updateError, newCommit,
    confirmUpdate,
    openUpdateModal: () => { setUpdateState("confirm"); setUpdateError(null); setNewCommit(null) },
    closeUpdateModal: () => setUpdateState("idle"),
  }
}
