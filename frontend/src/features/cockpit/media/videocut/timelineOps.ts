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

export const MIN_CLIP_DURATION = 0.1

/** Teilt einen Clip an der absoluten Timeline-Sekunde t in zwei Clips.
 *  Liegt t nicht echt im Clip-Inneren (mit Mindestabstand), bleibt tl unverändert. */
export function splitClipAt(tl: MediaTimeline, trackId: string, clipId: string, t: number): MediaTimeline {
  return {
    ...tl,
    tracks: tl.tracks.map((track) => {
      if (track.id !== trackId) return track
      const clips = track.clips.flatMap((c) => {
        if (c.id !== clipId) return [c]
        const offset = t - c.start
        if (offset < MIN_CLIP_DURATION || offset > c.duration - MIN_CLIP_DURATION) return [c]
        const left = { ...c, duration: offset }
        const right = {
          ...c,
          id: genId("clip"),
          start: t,
          source_in: (c.source_in ?? 0) + offset,
          duration: c.duration - offset,
        }
        return [left, right]
      })
      return { ...track, clips }
    }),
  }
}

/** Trimmt eine Clip-Kante. edge="start": linke Kante auf newStart (Timeline-Sek);
 *  edge="end": rechte Kante auf newEnd. Hält Mindestdauer und source_in ≥ 0 ein. */
export function trimClipEdge(
  tl: MediaTimeline,
  trackId: string,
  clipId: string,
  edge: "start" | "end",
  value: number,
): MediaTimeline {
  return {
    ...tl,
    tracks: tl.tracks.map((track) => {
      if (track.id !== trackId) return track
      return {
        ...track,
        clips: track.clips.map((c) => {
          if (c.id !== clipId) return c
          if (edge === "end") {
            const duration = Math.max(MIN_CLIP_DURATION, value - c.start)
            return { ...c, duration }
          }
          // edge === "start": linke Kante verschieben, source_in mitziehen.
          const sourceIn = c.source_in ?? 0
          const maxStart = c.start + c.duration - MIN_CLIP_DURATION
          // delta so begrenzen, dass source_in ≥ 0 bleibt.
          let newStart = Math.min(value, maxStart)
          let delta = newStart - c.start
          if (sourceIn + delta < 0) { delta = -sourceIn; newStart = c.start + delta }
          return { ...c, start: Math.max(0, newStart), source_in: sourceIn + delta, duration: c.duration - delta }
        }),
      }
    }),
  }
}
