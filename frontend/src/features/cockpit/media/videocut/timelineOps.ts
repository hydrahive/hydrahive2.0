import type { MediaCutPoint, MediaTimeline, MediaTimelineTrack } from "../../mediaWorkspaceApi"

/** Feste UI-Spuren des Schnittpults → Timeline-Track-Kinds. */
export const CUT_TRACKS = [
  { id: "vid1", name: "Video 1", kind: "video" as const },
  { id: "vid2", name: "Video 2", kind: "video" as const },
  { id: "music", name: "Musik", kind: "music" as const },
  { id: "fx", name: "Effekt", kind: "audio" as const },
  { id: "voice", name: "Sprache", kind: "voice" as const },
]

export const IMAGE_DEFAULT_DURATION = 5
export const AUDIO_FALLBACK_DURATION = 30

/** Stellt sicher, dass alle festen Spuren + ein cut_points-Array existieren. */
export function withDefaultTracks(timeline: MediaTimeline): MediaTimeline {
  const existing = new Map(timeline.tracks.map((t) => [t.id, t]))
  const tracks: MediaTimelineTrack[] = CUT_TRACKS.map((def) =>
    existing.get(def.id) ?? { id: def.id, name: def.name, kind: def.kind, muted: false, clips: [] },
  )
  return { ...timeline, tracks, cut_points: timeline.cut_points ?? [] }
}

export function trackEnd(track: MediaTimelineTrack): number {
  return track.clips.reduce((max, clip) => Math.max(max, clip.start + clip.duration), 0)
}

/** Dauer einer Audio-/Videodatei clientseitig über Element-Metadata ermitteln. */
export function probeDuration(url: string, kind: "audio" | "video"): Promise<number | null> {
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

const genId = (prefix: string) => `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`

// --- reine Timeline-Transformationen (immer neues Objekt) ---

export function setClipStart(tl: MediaTimeline, trackId: string, clipId: string, start: number): MediaTimeline {
  return {
    ...tl,
    tracks: tl.tracks.map((track) =>
      track.id !== trackId
        ? track
        : { ...track, clips: track.clips.map((c) => (c.id === clipId ? { ...c, start: Math.max(0, start) } : c)) },
    ),
  }
}

export function removeClipFrom(tl: MediaTimeline, trackId: string, clipId: string): MediaTimeline {
  return {
    ...tl,
    tracks: tl.tracks.map((track) =>
      track.id === trackId ? { ...track, clips: track.clips.filter((c) => c.id !== clipId) } : track,
    ),
  }
}

export function appendClip(tl: MediaTimeline, trackId: string, assetId: string, duration: number): MediaTimeline {
  return {
    ...tl,
    tracks: tl.tracks.map((track) => {
      if (track.id !== trackId) return track
      const clip = { id: genId("clip"), asset_id: assetId, start: trackEnd(track), duration, source_in: 0, volume: 1 }
      return { ...track, clips: [...track.clips, clip] }
    }),
  }
}

export function addCut(tl: MediaTimeline, time: number): { timeline: MediaTimeline; cut: MediaCutPoint } {
  const cut: MediaCutPoint = { id: genId("cut"), time: Math.max(0, time), effect: "cut", duration: 0 }
  return { timeline: { ...tl, cut_points: [...(tl.cut_points ?? []), cut] }, cut }
}

export function patchCut(tl: MediaTimeline, cutId: string, patch: Partial<MediaCutPoint>): MediaTimeline {
  return {
    ...tl,
    cut_points: (tl.cut_points ?? []).map((cp) => (cp.id === cutId ? { ...cp, ...patch } : cp)),
  }
}

export function removeCut(tl: MediaTimeline, cutId: string): MediaTimeline {
  return { ...tl, cut_points: (tl.cut_points ?? []).filter((cp) => cp.id !== cutId) }
}
