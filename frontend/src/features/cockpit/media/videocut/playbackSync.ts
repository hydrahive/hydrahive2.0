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

/** Startet die Wiedergabe robust gegen die Autoplay-Policy: Ein Video MIT Ton
 *  darf ohne User-Geste nicht auto-starten → play() rejected. In dem Fall
 *  stummschalten und erneut versuchen (Bild läuft, Ton kommt beim ersten
 *  echten Klick/Transport-Tick dazu). Verhindert das „nur Standbild". */
function safePlay(el: HTMLMediaElement) {
  el.play().catch(() => {
    if (!el.muted) {
      el.muted = true
      el.play().catch(() => {})
    }
  })
}

/** Koppelt ein <video>/<audio>-Element an die Master-Clock — ohne „Daumenkino".
 *
 *  Während der Wiedergabe läuft das Element mit seiner NATIVEN Clock frei und
 *  wird NICHT pro Frame nachgezogen; nur einmal beim Play-Start bzw. beim
 *  Clip-Wechsel (via key-Remount) an die Soll-Position geseekt. Im pausierten
 *  Zustand folgt es dem Sollwert (Scrub/Cursor). */
export function useMediaSync(
  ref: RefObject<HTMLMediaElement | null>,
  { localTime, playing, active, volume = 1, muted = false }: SyncOptions,
): void {
  const localTimeRef = useRef(localTime)
  useEffect(() => { localTimeRef.current = localTime })

  // Lautstärke/Mute.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.volume = Math.max(0, Math.min(1, volume))
    el.muted = muted
  }, [ref, volume, muted])

  // Play/Pause + einmaliger Seek beim Start der Wiedergabe. Retry via `canplay`,
  // falls das Video beim Play-Start noch nicht genug gepuffert hat.
  useEffect(() => {
    const el = ref.current
    if (!el) return

    if (!active) {
      if (!el.paused) el.pause()
      return
    }

    if (!playing) {
      if (!el.paused) el.pause()
      return
    }

    const startPlayback = () => {
      if (Math.abs(el.currentTime - localTimeRef.current) > 0.25) {
        try { el.currentTime = localTimeRef.current } catch { /* Metadata noch nicht bereit */ }
      }
      if (el.paused) safePlay(el)
    }

    if (el.readyState >= 2) {
      startPlayback()
    } else {
      el.addEventListener("canplay", startPlayback, { once: true })
      return () => el.removeEventListener("canplay", startPlayback)
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
