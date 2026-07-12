import { useEffect, type RefObject } from "react"

/** Ab welchem Drift (Sekunden) currentTime des Elements nachgezogen wird.
 *  Grobe Sync reicht für die Preview — häufiges Nachziehen würde ruckeln. */
const DRIFT_THRESHOLD = 0.3

interface SyncOptions {
  /** Lokale Soll-Position im Medium (Sekunden ab Clip-Start). */
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

/** Hält ein <video>/<audio>-Element grob an der Master-Clock.
 *  - Drift > Schwelle → currentTime nachziehen
 *  - playing/active steuern play()/pause()
 *  play() kann rejecten (Autoplay-Policy) — bewusst verschluckt. */
export function useMediaSync(
  ref: RefObject<HTMLMediaElement | null>,
  { localTime, playing, active, volume = 1, muted = false }: SyncOptions,
): void {
  // Lautstärke/Mute getrennt anwenden (kein Re-Sync nötig).
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.volume = Math.max(0, Math.min(1, volume))
    el.muted = muted
  }, [ref, volume, muted])

  useEffect(() => {
    const el = ref.current
    if (!el) return

    if (!active) {
      if (!el.paused) el.pause()
      return
    }

    if (Math.abs(el.currentTime - localTime) > DRIFT_THRESHOLD) {
      try {
        el.currentTime = localTime
      } catch {
        /* Metadata evtl. noch nicht geladen — nächster Tick korrigiert. */
      }
    }

    if (playing && el.paused) {
      void el.play().catch(() => {})
    } else if (!playing && !el.paused) {
      el.pause()
    }
  }, [ref, localTime, playing, active])
}
