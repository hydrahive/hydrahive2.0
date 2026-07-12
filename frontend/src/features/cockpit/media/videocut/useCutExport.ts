import { useCallback, useState } from "react"
import { fileUrl } from "@/modules/atelier/api"
import { mediaWorkspaceApi } from "../../mediaWorkspaceApi"
import { CUT_SLUG } from "./api"

export type ExportStatus = "idle" | "running" | "done" | "error"

export interface ExportResult {
  downloadUrl: string
  duration: number
}

/** Rendert den Schnitt serverseitig (FFmpeg) und liefert einen Download-Link.
 *  Der Export läuft synchron im Request — für lange Timelines kann das dauern
 *  (Hintergrund-Job wäre eine spätere Ausbaustufe). */
export function useCutExport(projectId: string) {
  const [status, setStatus] = useState<ExportStatus>("idle")
  const [result, setResult] = useState<ExportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async () => {
    setStatus("running")
    setError(null)
    setResult(null)
    try {
      const res = await mediaWorkspaceApi.exportTimeline(projectId, CUT_SLUG)
      setResult({ downloadUrl: fileUrl(res.path), duration: res.duration })
      setStatus("done")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export fehlgeschlagen.")
      setStatus("error")
    }
  }, [projectId])

  const reset = useCallback(() => {
    setStatus("idle")
    setResult(null)
    setError(null)
  }, [])

  return { status, result, error, run, reset }
}
