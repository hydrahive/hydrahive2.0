import { useEffect, useRef, type RefObject } from "react"

interface SyncOptions {
  /** Soll-Position im Medium (Sekunden ab Clip-Start, inkl. source_in). */
  localTime: number
  /** Läuft die Master-Clock? */
  playing: boolean
  /** Ist dieses Element gerade aktiv (aktiver Clip vorhanden)? */
  active: boolean
  /** Lautstärke 0..1. */
  volume?: number
  /** Spur stummgeschaltet. */
  muted?: boolean
}

/** Koppelt ein <video>/<audio>-Element an die Master-Clock — ohne „Daumenkino".
 *
 *  Kernidee: Während der Wiedergabe läuft das Element mit seiner NATIVEN Clock
 *  frei und wird NICHT pro Frame nachgezogen. Es wird nur einmal an den Sollwert
 *  geseekt, wenn die Wiedergabe startet (oder das Element via key neu mountet).
 *  Im pausierten Zustand folgt es dagegen jederzeit dem Sollwert (Scrub/Cursor).
 *  Dadurch kämpfen Master-Clock und Video-Playback nicht mehr gegeneinander. */
export function useMediaSync(
  ref: RefObject<HTMLMediaElement | null>,
  { localTime, playing, active, volume = 1, muted = false }: SyncOptions,
): void {
  // Aktuellen Sollwert in einem Ref halten, damit der Play-Start-Effekt ihn
  // lesen kann, ohne bei jeder Positionsänderung neu zu laufen.
  const localTimeRef = useRef(localTime)
  useEffect(() => { localTimeRef.current = localTime })

  // Lautstärke/Mute.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.volume = Math.max(0, Math.min(1, volume))
    el.muted = muted
  }, [ref, volume, muted])

  // Play/Pause + einmaliger Seek beim Start der Wiedergabe.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (!active) {
      if (!el.paused) el.pause()
      return
    }
    if (playing) {
      // Einmal an die Soll-Position setzen, dann frei laufen lassen.
      if (Math.abs(el.currentTime - localTimeRef.current) > 0.25) {
        try { el.currentTime = localTimeRef.current } catch { /* Metadata noch nicht bereit */ }
      }
      if (el.paused) void el.play().catch(() => {})
    } else if (!el.paused) {
      el.pause()
    }
  }, [ref, playing, active])

  // Nur im pausierten Zustand dem Sollwert folgen (Scrub / Justage-Cursor).
  useEffect(() => {
    const el = ref.current
    if (!el || !active || playing) return
    if (Math.abs(el.currentTime - localTime) > 0.05) {
      try { el.currentTime = localTime } catch { /* Metadata noch nicht bereit */ }
    }
  }, [ref, localTime, playing, active])
}
