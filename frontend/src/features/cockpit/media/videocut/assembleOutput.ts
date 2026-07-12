import type { MediaCutPoint, MediaTimeline } from "../../mediaWorkspaceApi"
import { clipAt, type ActiveClip } from "./useCutPlayback"

/** Sortierte Schnittpunkt-Zeiten der Timeline (aufsteigend). */
export function sortedCutTimes(timeline: MediaTimeline): number[] {
  return (timeline.cut_points ?? []).map((cp) => cp.time).sort((a, b) => a - b)
}

/** Aktive Video-Spur an Position t nach A/B-Roll-Regel:
 *  Start auf vid1, jeder Schnittpunkt links von t toggelt vid1↔vid2.
 *  Gerade Anzahl → vid1, ungerade → vid2. */
export function activeTrackId(timeline: MediaTimeline, t: number): "vid1" | "vid2" {
  const before = sortedCutTimes(timeline).filter((time) => time <= t).length
  return before % 2 === 0 ? "vid1" : "vid2"
}

/** Sichtbarer Clip im Output an Position t: aktive Spur nach Schnittpunkt-Toggle,
 *  mit Fallback auf die andere Video-Spur, falls die aktive dort eine Lücke hat. */
export function activeVideoAt(timeline: MediaTimeline, t: number): ActiveClip | null {
  const primary = activeTrackId(timeline, t)
  const fallback = primary === "vid1" ? "vid2" : "vid1"
  for (const id of [primary, fallback]) {
    const track = timeline.tracks.find((tr) => tr.id === id)
    if (!track) continue
    const hit = clipAt(track, t)
    if (hit) return hit
  }
  return null
}

/** Für die UI: nächster/aktueller CutPoint-Zustand (nur Anzahl, z.B. Zähler). */
export function cutPointCount(timeline: MediaTimeline): number {
  return (timeline.cut_points ?? []).length
}

export type { MediaCutPoint }
