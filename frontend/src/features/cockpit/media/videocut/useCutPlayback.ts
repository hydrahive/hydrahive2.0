import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type { MediaTimeline, MediaTimelineClip, MediaTimelineTrack } from "../../mediaWorkspaceApi"

/** Aktiver Clip einer Spur samt lokaler Position (Sekunden ab Clip-Start). */
export interface ActiveClip {
  track: MediaTimelineTrack
  clip: MediaTimelineClip
  localTime: number
}

/** Gesamtlänge der Timeline = Ende des spätesten Clips. */
export function timelineDuration(timeline: MediaTimeline | null): number {
  if (!timeline) return 0
  let end = 0
  for (const track of timeline.tracks) {
    for (const clip of track.clips) end = Math.max(end, clip.start + clip.duration)
  }
  return end
}

/** Aktiven Clip einer Spur an Position t finden (letzter, der t abdeckt). */
export function clipAt(track: MediaTimelineTrack, t: number): ActiveClip | null {
  let hit: MediaTimelineClip | null = null
  for (const clip of track.clips) {
    if (t >= clip.start && t < clip.start + clip.duration) hit = clip
  }
  return hit ? { track, clip: hit, localTime: t - hit.start } : null
}

/** Timecode HH:MM:SS aus Sekunden. */
export function timecode(sec: number): string {
  const s = Math.max(0, Math.floor(sec))
  const hh = String(Math.floor(s / 3600)).padStart(2, "0")
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0")
  const ss = String(s % 60).padStart(2, "0")
  return `${hh}:${mm}:${ss}`
}

/** Master-Clock des Schnittpults. Führt currentTime per wall-clock-rAF und
 *  liefert Transport-Steuerung. Media-Elemente folgen dieser Clock (grobe Sync). */
export function useCutPlayback(timeline: MediaTimeline | null) {
  const duration = useMemo(() => timelineDuration(timeline), [timeline])
  const [currentTime, setCurrentTime] = useState(0)
  const [playing, setPlaying] = useState(false)

  const rafRef = useRef<number | null>(null)
  // Ankerpunkt: wall-clock-Zeitstempel + Timeline-Position beim Play-Start.
  const anchorRef = useRef<{ wall: number; time: number } | null>(null)
  const durationRef = useRef(duration)
  useEffect(() => {
    durationRef.current = duration
  }, [duration])

  const stopLoop = useCallback(() => {
    if (rafRef.current != null) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    anchorRef.current = null
  }, [])

  // rAF-Schleife während der Wiedergabe.
  useEffect(() => {
    if (!playing) {
      stopLoop()
      return
    }
    const tick = () => {
      const anchor = anchorRef.current
      if (!anchor) return
      const elapsed = (performance.now() - anchor.wall) / 1000
      const next = anchor.time + elapsed
      if (next >= durationRef.current) {
        setCurrentTime(durationRef.current)
        setPlaying(false)
        return
      }
      setCurrentTime(next)
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return stopLoop
  }, [playing, stopLoop])

  const play = useCallback(() => {
    if (durationRef.current <= 0) return
    setPlaying((wasPlaying) => {
      if (wasPlaying) return true
      // Am Ende erneut → von vorn.
      const startAt = currentTime >= durationRef.current ? 0 : currentTime
      anchorRef.current = { wall: performance.now(), time: startAt }
      if (startAt !== currentTime) setCurrentTime(startAt)
      return true
    })
  }, [currentTime])

  const pause = useCallback(() => setPlaying(false), [])

  const stop = useCallback(() => {
    setPlaying(false)
    setCurrentTime(0)
  }, [])

  const seek = useCallback((t: number) => {
    const clamped = Math.max(0, Math.min(t, durationRef.current))
    setCurrentTime(clamped)
    // Bei laufender Wiedergabe Anker neu setzen, damit die Clock weiterläuft.
    if (anchorRef.current) anchorRef.current = { wall: performance.now(), time: clamped }
  }, [])

  const toStart = useCallback(() => seek(0), [seek])
  const toEnd = useCallback(() => {
    setPlaying(false)
    setCurrentTime(durationRef.current)
  }, [])

  const togglePlay = useCallback(() => {
    if (playing) pause()
    else play()
  }, [playing, play, pause])

  return { currentTime, duration, playing, play, pause, stop, seek, toStart, toEnd, togglePlay }
}
