import { useCallback, useEffect, useRef, useState } from "react"
import type { MediaAssetReference } from "../../mediaProjectsApi"
import type { MediaTimeline, MediaTimelineTrack } from "../../mediaWorkspaceApi"
import { ensureAssetRef, ensureCutProject, loadTimelineAndAssets, saveTimeline, type LibraryItem } from "./api"

/** Feste UI-Spuren des Schnittpults → Timeline-Track-Kinds. */
export const CUT_TRACKS = [
  { id: "vid1", name: "Video 1", kind: "video" as const },
  { id: "vid2", name: "Video 2", kind: "video" as const },
  { id: "music", name: "Musik", kind: "music" as const },
  { id: "fx", name: "Effekt", kind: "audio" as const },
  { id: "voice", name: "Sprache", kind: "voice" as const },
]

export const IMAGE_DEFAULT_DURATION = 5
const AUDIO_FALLBACK_DURATION = 30

function withDefaultTracks(timeline: MediaTimeline): MediaTimeline {
  const existing = new Map(timeline.tracks.map((t) => [t.id, t]))
  const tracks: MediaTimelineTrack[] = CUT_TRACKS.map((def) =>
    existing.get(def.id) ?? { id: def.id, name: def.name, kind: def.kind, muted: false, clips: [] },
  )
  return { ...timeline, tracks }
}

function trackEnd(track: MediaTimelineTrack): number {
  return track.clips.reduce((max, clip) => Math.max(max, clip.start + clip.duration), 0)
}

/** Dauer einer Audio-/Videodatei clientseitig über Element-Metadata ermitteln. */
function probeDuration(url: string, kind: "audio" | "video"): Promise<number | null> {
  return new Promise((resolve) => {
    const el = document.createElement(kind)
    const done = (value: number | null) => { el.src = ""; resolve(value) }
    el.preload = "metadata"
    el.onloadedmetadata = () => done(Number.isFinite(el.duration) && el.duration > 0 ? el.duration : null)
    el.onerror = () => done(null)
    setTimeout(() => done(null), 8000)
    el.src = url
  })
}

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

      const next: MediaTimeline = {
        ...timeline,
        tracks: timeline.tracks.map((track) => {
          if (track.id !== trackId) return track
          const clip = {
            id: `clip-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
            asset_id: ref.id,
            start: trackEnd(track),
            duration,
            source_in: 0,
            volume: 1,
          }
          return { ...track, clips: [...track.clips, clip] }
        }),
      }
      await persist(next)
    } catch {
      setError("Clip konnte nicht hinzugefügt werden.")
    }
  }, [timeline, assets, projectId, persist])

  const removeClip = useCallback((trackId: string, clipId: string) => {
    if (!timeline) return
    const next: MediaTimeline = {
      ...timeline,
      tracks: timeline.tracks.map((track) =>
        track.id === trackId ? { ...track, clips: track.clips.filter((c) => c.id !== clipId) } : track,
      ),
    }
    void persist(next)
  }, [timeline, persist])

  return { timeline, assets, loading, saving, error, addClip, removeClip }
}
