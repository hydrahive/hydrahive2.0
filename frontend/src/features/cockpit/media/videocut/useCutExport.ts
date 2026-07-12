import { useCallback, useEffect, useState } from "react"
import { fileUrl } from "@/modules/atelier/api"
import { mediaWorkspaceApi, type MediaExportEntry } from "../../mediaWorkspaceApi"
import { CUT_SLUG } from "./api"

export type ExportStatus = "idle" | "running" | "done" | "error"

/** Rendert den Schnitt serverseitig (FFmpeg) und verwaltet die Liste der
 *  fertigen Filme (persistente Export-Historie). */
export function useCutExport(projectId: string) {
  const [status, setStatus] = useState<ExportStatus>("idle")
  const [error, setError] = useState<string | null>(null)
  const [exports, setExports] = useState<MediaExportEntry[]>([])

  const refresh = useCallback(async () => {
    try {
      setExports(await mediaWorkspaceApi.listExports(projectId, CUT_SLUG))
    } catch {
      /* Liste ist optional — Fehler still schlucken. */
    }
  }, [projectId])

  // Initiales Laden der Export-Historie (setState erfolgt asynchron nach await).
  useEffect(() => {
    if (!projectId) return
    let alive = true
    void mediaWorkspaceApi.listExports(projectId, CUT_SLUG)
      .then((list) => { if (alive) setExports(list) })
      .catch(() => { /* Liste optional */ })
    return () => { alive = false }
  }, [projectId])

  const run = useCallback(async () => {
    setStatus("running")
    setError(null)
    try {
      await mediaWorkspaceApi.exportTimeline(projectId, CUT_SLUG)
      setStatus("done")
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export fehlgeschlagen.")
      setStatus("error")
    }
  }, [projectId, refresh])

  const remove = useCallback(async (name: string) => {
    try {
      await mediaWorkspaceApi.deleteExport(projectId, CUT_SLUG, name)
      await refresh()
    } catch {
      /* Fehler still — Liste bleibt wie sie ist. */
    }
  }, [projectId, refresh])

  return { status, error, exports, run, remove, downloadUrl: (path: string) => fileUrl(path) }
}
