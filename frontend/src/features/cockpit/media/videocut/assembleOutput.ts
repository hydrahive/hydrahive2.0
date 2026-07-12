import type { MediaCutPoint, MediaTimeline, MediaTransitionEffect } from "../../mediaWorkspaceApi"
import { clipAt, type ActiveClip } from "./useCutPlayback"

/** Nach Zeit sortierte Schnittpunkte. */
export function sortedCuts(timeline: MediaTimeline): MediaCutPoint[] {
  return [...(timeline.cut_points ?? [])].sort((a, b) => a.time - b.time)
}

/** Aktive Video-Spur nach n Schnittpunkten: gerade → vid1, ungerade → vid2. */
function trackForIndex(n: number): "vid1" | "vid2" {
  return n % 2 === 0 ? "vid1" : "vid2"
}

/** Aktive Video-Spur an Position t (Anzahl Schnittpunkte ≤ t bestimmt Toggle). */
export function activeTrackId(timeline: MediaTimeline, t: number): "vid1" | "vid2" {
  const n = sortedCuts(timeline).filter((cp) => cp.time <= t).length
  return trackForIndex(n)
}

/** Clip einer Video-Spur an t, mit Fallback auf die andere Video-Spur bei Lücke. */
function clipOnTrackWithFallback(timeline: MediaTimeline, trackId: "vid1" | "vid2", t: number): ActiveClip | null {
  const other = trackId === "vid1" ? "vid2" : "vid1"
  for (const id of [trackId, other]) {
    const track = timeline.tracks.find((tr) => tr.id === id)
    if (!track) continue
    const hit = clipAt(track, t)
    if (hit) return hit
  }
  return null
}

/** Sichtbarer Clip im Output an Position t (ohne Übergangs-Layer). */
export function activeVideoAt(timeline: MediaTimeline, t: number): ActiveClip | null {
  return clipOnTrackWithFallback(timeline, activeTrackId(timeline, t), t)
}

export interface OutputLayers {
  base: ActiveClip | null
  /** Overlay-Layer während eines Übergangsfensters, sonst null. */
  overlay: ActiveClip | null
  /** 0..1 innerhalb des Fensters; 0 außerhalb. */
  progress: number
  effect: MediaTransitionEffect
}

/** Übergangsfenster eines Schnittpunkts: [time − d/2, time + d/2]. */
function windowOf(cp: MediaCutPoint): { from: number; to: number } | null {
  const d = cp.duration ?? 0
  const effect = cp.effect ?? "cut"
  if (effect === "cut" || d <= 0) return null
  return { from: cp.time - d / 2, to: cp.time + d / 2 }
}

/** Output-Layer an Position t: base immer, overlay+progress+effect im Fenster.
 *  Der Schnittpunkt-Index bestimmt base = Spur davor, overlay = Spur danach. */
export function outputLayersAt(timeline: MediaTimeline, t: number): OutputLayers {
  const cuts = sortedCuts(timeline)

  // Aktives Übergangsfenster suchen (erstes, das t enthält).
  for (let i = 0; i < cuts.length; i++) {
    const win = windowOf(cuts[i])
    if (!win || t < win.from || t >= win.to) continue
    const before = trackForIndex(i)       // Schnittpunkte VOR diesem: i
    const after = trackForIndex(i + 1)    // nach diesem Schnittpunkt
    const progress = (t - win.from) / (win.to - win.from)
    return {
      base: clipOnTrackWithFallback(timeline, before, t),
      overlay: clipOnTrackWithFallback(timeline, after, t),
      progress,
      effect: cuts[i].effect ?? "cut",
    }
  }

  // Kein Übergang aktiv → einzelne Spur.
  return { base: activeVideoAt(timeline, t), overlay: null, progress: 0, effect: "cut" }
}

export function cutPointCount(timeline: MediaTimeline): number {
  return (timeline.cut_points ?? []).length
}

export type { MediaCutPoint }
