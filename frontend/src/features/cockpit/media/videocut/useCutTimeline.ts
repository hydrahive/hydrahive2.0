import { useCallback, useEffect, useRef, useState } from "react"
import type { MediaAssetReference } from "../../mediaProjectsApi"
import type { MediaCutPoint, MediaTimeline } from "../../mediaWorkspaceApi"
import { ensureAssetRef, ensureCutProject, loadTimelineAndAssets, saveTimeline, type LibraryItem } from "./api"
import {
  addCut, appendClip, AUDIO_FALLBACK_DURATION, CUT_TRACKS, IMAGE_DEFAULT_DURATION,
  patchCut, probeDuration, removeClipFrom, removeCut, setClipStart, withDefaultTracks,
} from "./timelineOps"

// Re-Export für bestehende Importe (TrackArea, ClipLibrary, InputMonitor …).
export { CUT_TRACKS, IMAGE_DEFAULT_DURATION }

export function useCutTimeline(projectId: string) {
  const [timeline, setTimeline] = useState<MediaTimeline | null>(null)
  const [assets, setAssets] = useState<MediaAssetReference[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const initialized = useRef<string | null>(null)
  const loading = timeline === null && error === null

  useEffect(() => {
    if (!projectId || initialized.current === projectId) return
    initialized.current = projectId
    ;(async () => {
      try {
        await ensureCutProject(projectId)
        const { timeline: tl, assets: refs } = await loadTimelineAndAssets(projectId)
        setTimeline(withDefaultTracks(tl))
        setAssets(refs)
      } catch {
        setError("Schnitt-Projekt konnte nicht geladen werden.")
      }
    })()
  }, [projectId])

  const persist = useCallback(async (next: MediaTimeline) => {
    setTimeline(next)
    setSaving(true)
    setError(null)
    try {
      await saveTimeline(projectId, next)
    } catch {
      setError("Timeline konnte nicht gespeichert werden.")
    } finally {
      setSaving(false)
    }
  }, [projectId])

  /** Legt einen Bibliothekseintrag ans Ende der Ziel-Spur. */
  const addClip = useCallback(async (item: LibraryItem, trackId: string, previewUrl: string | null) => {
    if (!timeline) return
    setError(null)
    try {
      const ref = await ensureAssetRef(projectId, item, assets)
      if (!assets.some((a) => a.id === ref.id)) setAssets((cur) => [...cur, ref])

      let duration = item.duration
      if (duration == null && previewUrl && (item.kind === "audio" || item.kind === "video")) {
        duration = await probeDuration(previewUrl, item.kind === "audio" ? "audio" : "video")
      }
      if (duration == null) duration = item.kind === "image" ? IMAGE_DEFAULT_DURATION : AUDIO_FALLBACK_DURATION

      await persist(appendClip(timeline, trackId, ref.id, duration))
    } catch {
      setError("Clip konnte nicht hinzugefügt werden.")
    }
  }, [timeline, assets, projectId, persist])

  const removeClip = useCallback((trackId: string, clipId: string) => {
    if (timeline) void persist(removeClipFrom(timeline, trackId, clipId))
  }, [timeline, persist])

  /** Setzt clip.start lokal (ohne PUT) — für flüssiges Ziehen. */
  const previewClipStart = useCallback((trackId: string, clipId: string, start: number) => {
    setTimeline((cur) => (cur ? setClipStart(cur, trackId, clipId, start) : cur))
  }, [])

  const moveClip = useCallback((trackId: string, clipId: string, start: number) => {
    if (timeline) void persist(setClipStart(timeline, trackId, clipId, start))
  }, [timeline, persist])

  /** Fügt am Zeitpunkt time einen Schnittpunkt hinzu und gibt dessen ID zurück. */
  const addCutPoint = useCallback((time: number): string | null => {
    if (!timeline) return null
    const { timeline: next, cut } = addCut(timeline, time)
    void persist(next)
    return cut.id
  }, [timeline, persist])

  /** Setzt cut.time lokal (ohne PUT) — für flüssiges Ziehen. */
  const previewCutPoint = useCallback((cutId: string, time: number) => {
    setTimeline((cur) => (cur ? patchCut(cur, cutId, { time: Math.max(0, time) }) : cur))
  }, [])

  const moveCutPoint = useCallback((cutId: string, time: number) => {
    if (timeline) void persist(patchCut(timeline, cutId, { time: Math.max(0, time) }))
  }, [timeline, persist])

  /** Ändert Effekt/Dauer (o.ä.) eines Schnittpunkts und persistiert. */
  const updateCutPoint = useCallback((cutId: string, patch: Partial<MediaCutPoint>) => {
    if (timeline) void persist(patchCut(timeline, cutId, patch))
  }, [timeline, persist])

  const removeCutPoint = useCallback((cutId: string) => {
    if (timeline) void persist(removeCut(timeline, cutId))
  }, [timeline, persist])

  return {
    timeline, assets, loading, saving, error,
    addClip, removeClip, previewClipStart, moveClip,
    addCutPoint, previewCutPoint, moveCutPoint, updateCutPoint, removeCutPoint,
  }
}
