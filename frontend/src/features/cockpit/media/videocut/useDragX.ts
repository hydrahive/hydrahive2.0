import { useCallback, useEffect, useRef, useState } from "react"

interface DragState {
  startX: number
  startValue: number
}

interface UseDragXOptions {
  /** Pixel pro Sekunde der Timeline-Skala. */
  pxPerSecond: number
  /** Wird bei jeder Bewegung mit dem neuen (gesnappten) Wert in Sekunden gerufen. */
  onMove: (value: number) => void
  /** Beim Loslassen mit dem finalen Wert — z.B. zum Persistieren. */
  onCommit?: (value: number) => void
  /** Optionales Snapping: bekommt Rohwert, gibt gesnappten Wert zurück. */
  snap?: (value: number) => number
}

/** Horizontales Pointer-Dragging auf einer Zeitachse.
 *  Rechnet Pixel-Delta → Sekunden, wendet optionales Snapping an und meldet
 *  Werte über onMove/onCommit. Window-Listener → Drag läuft auch außerhalb des
 *  Elements weiter. Gibt einen Pointer-Down-Handler + `dragging`-Flag zurück. */
export function useDragX({ pxPerSecond, onMove, onCommit, snap }: UseDragXOptions) {
  const [dragging, setDragging] = useState(false)
  const stateRef = useRef<DragState | null>(null)
  // Callbacks in Refs halten → Listener müssen nicht neu gebunden werden.
  const cb = useRef({ onMove, onCommit, snap })
  useEffect(() => {
    cb.current = { onMove, onCommit, snap }
  })

  const start = useCallback((e: { clientX: number }, currentValue: number) => {
    stateRef.current = { startX: e.clientX, startValue: currentValue }
    setDragging(true)
  }, [])

  useEffect(() => {
    if (!dragging) return
    const compute = (clientX: number): number => {
      const s = stateRef.current
      if (!s) return 0
      const raw = s.startValue + (clientX - s.startX) / pxPerSecond
      const clamped = Math.max(0, raw)
      return cb.current.snap ? cb.current.snap(clamped) : clamped
    }
    const onPointerMove = (ev: PointerEvent) => cb.current.onMove(compute(ev.clientX))
    const onPointerUp = (ev: PointerEvent) => {
      const value = compute(ev.clientX)
      setDragging(false)
      stateRef.current = null
      cb.current.onCommit?.(value)
    }
    window.addEventListener("pointermove", onPointerMove)
    window.addEventListener("pointerup", onPointerUp)
    return () => {
      window.removeEventListener("pointermove", onPointerMove)
      window.removeEventListener("pointerup", onPointerUp)
    }
  }, [dragging, pxPerSecond])

  return { start, dragging }
}
